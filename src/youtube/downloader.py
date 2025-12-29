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

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

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
        self.cookies_file = settings.youtube_cookies_file

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

            # 创建视频专属文件夹
            video_folder = self.download_path / video.folder_name
            video_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建视频文件夹: {video_folder.name}")

            # 检查视频是否已存在（检查 _original.mp4 和最终嵌入的 .mp4）
            safe_title = self._sanitize_filename(video.title)
            original_video = video_folder / f"{safe_title}_original.mp4"
            final_video = video_folder / f"{safe_title}.mp4"

            if original_video.exists():
                logger.info(f"视频已存在，跳过下载: {original_video.name}")
                return original_video
            if final_video.exists():
                logger.info(f"视频已存在（最终版本），跳过下载: {final_video.name}")
                # 如果最终版本存在，需要检查是否有 _original，如果没有则重命名
                if not original_video.exists():
                    import shutil
                    shutil.copy(str(final_video), str(original_video))
                    logger.info(f"从最终视频创建原始副本: {original_video.name}")
                return original_video

            # 构建输出文件名（保存到视频专属文件夹）
            # 注意：视频文件下载后会重命名为 {title}_original.mp4
            output_template = str(video_folder / f"{safe_title}.%(ext)s")

            # 首先检查是否有字幕
            has_subs = await self._check_subtitles(video.url)
            if not has_subs:
                logger.info(f"该视频没有字幕: {video.title}")

            # 配置yt-dlp选项
            ydl_opts = {
                "outtmpl": output_template,
                "format": self._get_format_selector(),  # 使用配置的分辨率
                "ignoreerrors": True,
                "no_warnings": True,
                # 合并选项（用于1080p等需要合并视频和音频的情况）
                "merge_output_format": "mp4",  # 合并后输出为mp4
                # 字幕相关配置
                "writesubtitles": True,  # 下载可用字幕
                "writeautomaticsub": True,  # 下载自动生成的字幕
                "subtitleslangs": ["en"],  # 只下载英文字幕
                "subtitlesformat": "srt",  # 字幕格式
                # 封面图相关配置
                "writethumbnail": True,  # 下载封面图
                "thumbnail_format": "jpg",  # 封面图格式
                "keepvideo": False,  # 不保留中间文件
            }

            # 如果配置了cookies文件，添加cookies支持
            if self.cookies_file and Path(self.cookies_file).exists():
                ydl_opts["cookiefile"] = self.cookies_file
                logger.info(f"使用cookies文件: {self.cookies_file}")

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
                # 检查封面图是否下载成功
                await self._check_thumbnail_files(result)

                # 重命名原始视频为 {title}_original.mp4
                await self._rename_original_video(result)

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
        """检查字幕文件并重命名为标准格式"""
        try:
            parent_dir = video_path.parent
            base_name = video_path.stem  # 原始视频标题

            # 字幕文件可能的扩展名和语言标识
            sub_extensions = [".srt", ".vtt"]
            lang_patterns = [".en", ".eng", ".en-US", ""]

            found_en_sub = None

            # 查找英文字幕
            for ext in sub_extensions:
                for lang in lang_patterns:
                    # 检查 {标题}{语言标识}.{扩展名}
                    sub_file = parent_dir / f"{base_name}{lang}{ext}"
                    if sub_file.exists():
                        found_en_sub = sub_file
                        logger.info(f"找到英文字幕: {sub_file.name}")
                        break
                if found_en_sub:
                    break

            # 重命名英文字幕为 en.srt
            if found_en_sub:
                target_en = parent_dir / "en.srt"
                if found_en_sub != target_en:
                    # 如果是VTT格式，转换为SRT
                    if found_en_sub.suffix.lower() == ".vtt":
                        # 这里可以添加VTT转SRT的逻辑，暂时直接重命名
                        logger.warning(f"字幕为VTT格式，将重命名为.srt: {found_en_sub.name}")
                    found_en_sub.rename(target_en)
                    logger.info(f"英文字幕已重命名为: en.srt")
            else:
                logger.info("未找到英文字幕文件")

        except Exception as e:
            logger.debug(f"检查字幕文件失败: {str(e)}")

    async def _check_thumbnail_files(self, video_path: Path) -> None:
        """检查封面图文件并统一转换为JPG格式，命名为 cover.jpg"""
        try:
            parent_dir = video_path.parent
            base_name = video_path.stem  # 原始视频标题

            # 封面图可能的扩展名
            thumbnail_extensions = [".jpg", ".jpeg", ".png", ".webp"]

            found_thumbnails = []

            # 检查与视频同名的封面图文件
            for ext in thumbnail_extensions:
                thumbnail_file = parent_dir / f"{base_name}{ext}"
                if thumbnail_file.exists():
                    found_thumbnails.append(thumbnail_file)
                    logger.info(f"封面图已下载: {thumbnail_file.name}")

            # 检查 yt-dlp 可能生成的其他命名格式
            for ext in thumbnail_extensions:
                # 尝试查找 "封面图" 或 "thumbnail" 相关文件
                for pattern in [f"*{ext}", f"thumbnail*{ext}", f"*_thumbnail{ext}"]:
                    matches = list(parent_dir.glob(pattern))
                    for match in matches:
                        if match.is_file() and match not in found_thumbnails:
                            found_thumbnails.append(match)
                            logger.info(f"找到封面图: {match.name}")

            if found_thumbnails:
                # 统一转换为 cover.jpg
                cover_jpg = parent_dir / "cover.jpg"

                for thumb in found_thumbnails:
                    if thumb.suffix.lower() in [".jpg", ".jpeg"] and thumb.name != "cover.jpg":
                        # 已是JPG格式，直接重命名
                        thumb.rename(cover_jpg)
                        logger.info(f"封面图已重命名为: cover.jpg")
                        # 删除其他封面图
                        for other_thumb in found_thumbnails:
                            if other_thumb != thumb and other_thumb.exists():
                                try:
                                    other_thumb.unlink()
                                    logger.debug(f"删除重复封面图: {other_thumb.name}")
                                except Exception as e:
                                    logger.debug(f"删除封面图失败: {other_thumb.name}, {str(e)}")
                        break
                    else:
                        # 非JPG格式，转换并保存为 cover.jpg
                        if PILLOW_AVAILABLE:
                            try:
                                with Image.open(thumb) as img:
                                    # 转换为RGB模式（如果是RGBA等模式）
                                    if img.mode in ("RGBA", "P"):
                                        img = img.convert("RGB")
                                    # 保存为JPG格式
                                    img.save(cover_jpg, "JPEG", quality=95)
                                logger.info(f"封面图已转换为: cover.jpg")
                                # 删除原文件
                                try:
                                    thumb.unlink()
                                    logger.debug(f"删除原封面图: {thumb.name}")
                                except Exception as e:
                                    logger.debug(f"删除原封面图失败: {thumb.name}, {str(e)}")
                                # 删除其他封面图
                                for other_thumb in found_thumbnails:
                                    if other_thumb != thumb and other_thumb.exists():
                                        try:
                                            other_thumb.unlink()
                                            logger.debug(f"删除其他封面图: {other_thumb.name}")
                                        except Exception as e:
                                            logger.debug(f"删除封面图失败: {other_thumb.name}, {str(e)}")
                                break
                            except Exception as e:
                                logger.error(f"转换封面图失败: {thumb.name}, {str(e)}")
                        else:
                            logger.warning("Pillow未安装，无法转换封面图为JPG格式")

                logger.info("封面图保存为: cover.jpg")
            else:
                logger.info("未找到封面图文件")

        except Exception as e:
            logger.debug(f"检查封面图文件失败: {str(e)}")

    async def _rename_original_video(self, video_path: Path) -> None:
        """将原始视频重命名为 {title}_original.mp4"""
        try:
            parent_dir = video_path.parent
            base_name = video_path.stem  # 原始视频标题

            # 目标文件名：{title}_original.mp4
            original_name = f"{base_name}_original.mp4"
            original_path = parent_dir / original_name

            # 如果文件不叫 _original，则重命名
            if not video_path.name.endswith("_original.mp4"):
                if original_path.exists():
                    # 如果目标文件已存在，删除它
                    original_path.unlink()
                    logger.debug(f"删除已存在的原始视频文件: {original_name}")

                video_path.rename(original_path)
                logger.info(f"原始视频已重命名为: {original_name}")

        except Exception as e:
            logger.error(f"重命名原始视频失败: {str(e)}")

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
        """获取格式选择器

        YouTube的高分辨率视频（1080p+）通常是分离的视频和音频流（DASH格式），
        需要合并。这个格式选择器会优先选择单文件，然后回退到视频+音频合并。
        """
        quality_map = {
            "480p": "480",
            "720p": "720",
            "1080p": "1080",
        }

        height = quality_map.get(self.quality, "720")

        # 格式选择逻辑：
        # 1. 优先选择单文件mp4（video+audio在一起）
        # 2. 如果没有，选择视频流 + 最佳音频，然后合并
        # 3. 最后回退到任何可用格式
        format_selector = (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"  # 1080p mp4视频 + m4a音频
            f"bestvideo[height<={height}]+bestaudio/"  # 任意1080p视频 + 任意音频
            f"best[height<={height}][ext=mp4]/"  # 单文件720p mp4
            f"best[height<={height}]/"  # 单文件720p任意格式
            f"best"  # 最后回退到最佳可用格式
        )

        return format_selector

    def _check_file_size(self, info: Dict[str, Any]) -> bool:
        """检查文件大小是否符合要求"""
        filesize = info.get("filesize") or info.get("filesize_approx")
        if filesize:
            size_mb = filesize / (1024 * 1024)
            return size_mb <= self.max_size_mb
        return True  # 如果无法获取大小，允许下载

    def _find_downloaded_file(self, info: Dict[str, Any], template) -> Optional[Path]:
        """查找下载的文件"""
        try:
            # template 可能是字符串或字典（取决于 yt-dlp 版本）
            # 从 template 中提取视频文件夹路径
            video_folder = None

            if isinstance(template, dict):
                # 如果是字典格式，尝试从 'default' 键获取模板
                default_template = template.get('default', '')
                if default_template:
                    # 提取文件夹路径
                    import re
                    match = re.match(r'^(.+[\\/])[^\\/]*\.\%\(', default_template)
                    if match:
                        video_folder = Path(match.group(1))
            elif isinstance(template, str):
                # 如果是字符串格式
                import re
                match = re.match(r'^(.+[\\/])[^\\/]*\.\%\(', template)
                if match:
                    video_folder = Path(match.group(1))

            # 如果无法从 template 提取，从 info 中构建文件夹路径
            if video_folder is None:
                video_id = info.get("id", "")
                channel_title = self._sanitize_filename(info.get("uploader", "") or info.get("channel", ""))
                video_folder = self.download_path / f"{channel_title}_{video_id}"

            if not video_folder.exists():
                logger.error(f"视频文件夹不存在: {video_folder}")
                return None

            # 尝试根据标题构建文件名
            title = self._sanitize_filename(info.get("title", ""))

            # 可能的扩展名
            extensions = ["mp4", "webm", "mkv", "avi"]

            # 首先尝试完全匹配
            for ext in extensions:
                filename = f"{title}.{ext}"
                filepath = video_folder / filename
                if filepath.exists():
                    logger.info(f"找到视频文件: {filepath.name}")
                    return filepath

            # 如果找不到，搜索视频文件夹中所有视频文件，返回最新的
            for ext in extensions:
                matches = list(video_folder.glob(f"*.{ext}"))
                if matches:
                    # 返回最新的文件
                    latest = max(matches, key=lambda p: p.stat().st_mtime)
                    logger.info(f"找到最新视频文件: {latest.name}")
                    return latest

            logger.error(f"在 {video_folder} 中未找到视频文件")
            return None

        except Exception as e:
            logger.error(f"查找下载文件失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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

            # 如果配置了cookies文件，添加cookies支持
            if self.cookies_file and Path(self.cookies_file).exists():
                ydl_opts["cookiefile"] = self.cookies_file

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
