"""YouTube视频下载模块"""

import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime

try:
    import yt_dlp

    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

from ..utils.config import settings
from ..utils.logger import logger
from .models import YouTubeVideo


class YouTubeDownloader:
    """YouTube视频下载器"""

    def __init__(self) -> None:
        self.download_path = Path(settings.download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = settings.max_video_size_mb
        self.quality = settings.video_quality

        if not YT_DLP_AVAILABLE:
            logger.warning("yt-dlp模块不可用，将使用模拟下载")

    async def download_video(self, video: YouTubeVideo, progress_callback: Optional[Callable] = None) -> Optional[Path]:
        """下载视频"""
        if not YT_DLP_AVAILABLE:
            logger.error("yt-dlp不可用，无法下载视频")
            return None

        return await self._download_with_ytdlp(video, progress_callback)

    async def _download_with_ytdlp(
        self, video: YouTubeVideo, progress_callback: Optional[Callable] = None
    ) -> Optional[Path]:
        """使用yt-dlp下载视频"""
        try:
            logger.info(f"开始下载视频: {video.title}")

            # 构建输出文件名（不包含video_id）
            safe_title = self._sanitize_filename(video.title)
            output_template = str(self.download_path / f"{safe_title}.%(ext)s")

            # 首先检查是否有字幕
            has_subs = await self._check_subtitles(video.url)
            if not has_subs:
                logger.info(f"该视频没有字幕: {video.title}")

            # 配置yt-dlp选项
            ydl_opts = {
                "outtmpl": output_template,
                "format": "best[height<=720]/best",
                "ignoreerrors": True,
                "no_warnings": True,
                # 字幕相关配置
                "writesubtitles": True,  # 下载可用字幕
                "writeautomaticsub": True,  # 下载自动生成的字幕
                "subtitleslangs": ["en", "zh-Hans", "zh-Hant", "zh-CN"],  # 优先英文字幕，然后是简繁体中文
                "subtitlesformat": "srt",  # 字幕格式
                "keepvideo": False,  # 不保留中间文件
            }

            # 添加进度回调
            if progress_callback:
                ydl_opts["progress_hooks"] = [self._create_progress_hook(progress_callback)]

            # 在线程池中执行下载
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._download_sync, video.url, ydl_opts)

            if result:
                logger.info(f"下载完成: {result}")
                # 检查字幕文件是否下载成功
                await self._check_subtitle_files(result)
                return result
            else:
                logger.error(f"下载失败: {video.title}")
                return None

        except Exception as e:
            logger.error(f"下载视频失败: {video.title}, 错误: {str(e)}")
            return None

    async def _check_subtitles(self, url: str) -> bool:
        """检查视频是否有字幕"""
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,  # 不下载视频
            }

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                self._extract_info_sync,
                url,
                ydl_opts,
            )

            if not info:
                return False

            # 检查是否有字幕
            subtitles = info.get("subtitles", {})
            automatic_captions = info.get("automatic_captions", {})

            has_subs = bool(subtitles or automatic_captions)

            if has_subs:
                available_langs = list(subtitles.keys()) + list(automatic_captions.keys())
                logger.info(f"视频有可用字幕: {', '.join(set(available_langs))}")

            return has_subs

        except Exception as e:
            logger.debug(f"检查字幕失败: {str(e)}")
            return False

    async def _check_subtitle_files(self, video_path: Path) -> None:
        """检查字幕文件是否下载成功"""
        try:
            # 字幕文件可能的扩展名
            sub_extensions = [".srt", ".vtt", ".ass", ".lrc"]

            # 检查与视频同名的字幕文件
            base_name = video_path.stem
            parent_dir = video_path.parent

            found_subs = []
            for ext in sub_extensions:
                sub_file = parent_dir / f"{base_name}{ext}"
                if sub_file.exists():
                    found_subs.append(sub_file.name)
                    logger.info(f"字幕文件已下载: {sub_file.name}")

            if found_subs:
                logger.info(f"共下载 {len(found_subs)} 个字幕文件")
            else:
                logger.info("未找到字幕文件")

        except Exception as e:
            logger.debug(f"检查字幕文件失败: {str(e)}")

    def _download_sync(self, url: str, ydl_opts: Dict[str, Any]) -> Optional[Path]:
        """同步下载方法"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)

                # 检查文件大小
                if self._check_file_size(info):
                    # 下载视频
                    ydl.download([url])

                    # 查找下载的文件
                    return self._find_downloaded_file(info, ydl_opts["outtmpl"])
                else:
                    logger.warning(f"视频文件过大，跳过下载: {info.get('title', 'Unknown')}")
                    return None

        except Exception as e:
            logger.error(f"yt-dlp下载失败: {str(e)}")
            return None

    def _get_format_selector(self) -> str:
        """获取格式选择器"""
        quality_map = {
            "480p": "best[height<=480]",
            "720p": "best[height<=720]",
            "1080p": "best[height<=1080]",
        }

        base_format = quality_map.get(self.quality, "best[height<=720]")

        # 优先选择mp4格式，限制文件大小
        return f"({base_format}[ext=mp4]/best[ext=mp4]/{base_format}/best)[filesize<{self.max_size_mb}M]"

    def _check_file_size(self, info: Dict[str, Any]) -> bool:
        """检查文件大小是否符合要求"""
        filesize = info.get("filesize") or info.get("filesize_approx")
        if filesize:
            size_mb = filesize / (1024 * 1024)
            return size_mb <= self.max_size_mb
        return True  # 如果无法获取大小，允许下载

    def _find_downloaded_file(self, info: Dict[str, Any], template: str) -> Optional[Path]:
        """查找下载的文件"""
        try:
            # 尝试根据模板构建文件名
            title = self._sanitize_filename(info.get("title", ""))

            # 可能的扩展名
            extensions = ["mp4", "webm", "mkv", "avi"]

            for ext in extensions:
                filename = f"{title}.{ext}"
                filepath = self.download_path / filename
                if filepath.exists():
                    return filepath

            # 如果找不到，搜索目录中匹配标题的文件
            for ext in extensions:
                matches = list(self.download_path.glob(f"{title}*.{ext}"))
                if matches:
                    # 返回最新的文件
                    return max(matches, key=lambda p: p.stat().st_mtime)

            return None

        except Exception as e:
            logger.error(f"查找下载文件失败: {str(e)}")
            return None

    def _create_progress_hook(self, callback: Callable) -> Callable:
        """创建进度回调钩子"""

        def progress_hook(d):
            if d["status"] == "downloading":
                if "total_bytes" in d:
                    percent = d["downloaded_bytes"] / d["total_bytes"] * 100
                    callback(percent, d.get("speed", 0))
                elif "_percent_str" in d:
                    try:
                        percent = float(d["_percent_str"].replace("%", ""))
                        callback(percent, d.get("speed", 0))
                    except:
                        pass
            elif d["status"] == "finished":
                callback(100, 0)

        return progress_hook

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, "_")

        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]

        # 移除首尾空格和点
        filename = filename.strip(". ")

        return filename or "untitled"

    async def get_video_info(self, url: str) -> Optional[YouTubeVideo]:
        """获取视频信息"""
        if not YT_DLP_AVAILABLE:
            logger.error("yt-dlp不可用，无法获取视频信息")
            return None

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self._extract_info_sync, url)

            if info:
                return self._parse_video_info(info)

        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")

        return None

    def _extract_info_sync(self, url: str) -> Optional[Dict[str, Any]]:
        """同步提取视频信息"""
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        except Exception as e:
            logger.error(f"提取视频信息失败: {str(e)}")
            return None

    def _parse_video_info(self, info: Dict[str, Any]) -> YouTubeVideo:
        """解析视频信息"""
        from datetime import datetime

        # 解析发布时间
        upload_date = info.get("upload_date")
        if upload_date:
            published_at = datetime.strptime(upload_date, "%Y%m%d")
        else:
            published_at = datetime.now()

        return YouTubeVideo(
            video_id=info.get("id", ""),
            title=info.get("title", ""),
            description=info.get("description", ""),
            channel_title=info.get("uploader", ""),
            channel_id=info.get("channel_id", ""),
            published_at=published_at,
            duration=f"PT{info.get('duration', 0)}S",
            view_count=info.get("view_count", 0),
            like_count=info.get("like_count", 0),
            comment_count=info.get("comment_count", 0),
            thumbnail_url=info.get("thumbnail"),
            tags=info.get("tags", []),
            language=info.get("language", "en"),
            category_id=str(info.get("categories", [""])[0]) if info.get("categories") else None,
        )
