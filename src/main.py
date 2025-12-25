"""主程序入口"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm, Prompt
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
    )

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .utils.logger import logger
from .utils.config import settings
from .youtube.searcher import YouTubeSearcher
from .youtube.downloader import YouTubeDownloader
from .youtube.models import YouTubeVideo
from .bilibili.uploader import BilibiliUploader
from .bilibili.content_optimizer import BilibiliContentOptimizer
from .core.subtitle_processor import SubtitleProcessor
import re


class LocalVideo:
    """本地视频信息"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.filesize_mb = filepath.stat().st_size / (1024 * 1024)
        self.video_id = self._extract_video_id()
        self.title = self._extract_title()
        self.youtube_info = None

    def _extract_video_id(self) -> Optional[str]:
        """从文件名提取视频ID"""
        # 文件名格式: {video_id}_{title}.{ext}
        match = re.match(r"^([a-zA-Z0-9_-]{11})_", self.filename)
        if match:
            return match.group(1)
        # 如果没有video_id前缀，尝试从标题中提取（如可能）
        # 或者返回None，稍后可通过其他方式获取
        return None

    def _extract_title(self) -> str:
        """从文件名提取标题"""
        # 移除扩展名和video_id前缀
        name_without_ext = Path(self.filename).stem
        if self.video_id and name_without_ext.startswith(f"{self.video_id}_"):
            return name_without_ext[len(self.video_id) + 1:]
        return name_without_ext


class YouTubeToBilibili:
    """YouTube到B站视频搬运工具"""

    def __init__(self, enable_upload: bool = False, dry_run: bool = False, translate_subs: bool = False, embed_subs: bool = False) -> None:
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = self._create_fallback_console()

        self.searcher = YouTubeSearcher()
        self.downloader = YouTubeDownloader()
        self.subtitle_processor = SubtitleProcessor()
        self.enable_upload = enable_upload
        self.dry_run = dry_run  # 模拟模式，不上传
        self.translate_subs = translate_subs  # 是否翻译字幕
        self.embed_subs = embed_subs  # 是否嵌入字幕到视频

        # 初始化Bilibili上传相关组件
        if enable_upload:
            self.uploader = BilibiliUploader()
            self.content_optimizer = BilibiliContentOptimizer()
        else:
            self.uploader = None
            self.content_optimizer = None

    def _create_fallback_console(self):
        """创建备用控制台"""

        class FallbackConsole:
            def print(self, text, style=""):
                if style == "red":
                    print(f"❌ {text}")
                elif style == "green":
                    print(f"✅ {text}")
                elif style == "blue":
                    print(f"🔵 {text}")
                elif style == "yellow":
                    print(f"⚠️ {text}")
                else:
                    print(text)

        return FallbackConsole()

    async def search_and_download(self, max_videos: int = 10) -> List[YouTubeVideo]:
        """搜索并下载视频"""
        try:
            self.console.print("🔍 正在搜索计算机领域热门视频...", style="bold blue")

            # 搜索热门视频
            if RICH_AVAILABLE:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                ) as progress:
                    task = progress.add_task("搜索视频中...", total=None)
                    videos = await self.searcher.search_trending_cs_videos(max_videos)
                    progress.update(task, completed=True)
            else:
                print("搜索视频中...")
                videos = await self.searcher.search_trending_cs_videos(max_videos)

            if not videos:
                self.console.print("❌ 未找到符合条件的视频", style="red")
                return []

            # 显示搜索结果
            self._display_videos(videos)

            # 选择要下载的视频
            selected_videos = self._select_videos(videos)
            if not selected_videos:
                return []

            # 下载视频
            downloaded_videos = []

            if RICH_AVAILABLE:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.console,
                ) as progress:
                    for i, video in enumerate(selected_videos):
                        task = progress.add_task(
                            f"下载: {video.title[:30]}...", total=100
                        )

                        def update_progress(percent, speed):
                            progress.update(task, completed=percent)

                        try:
                            downloaded_path = await self.downloader.download_video(
                                video, update_progress
                            )

                            if downloaded_path:
                                video.downloaded_path = str(downloaded_path)
                                downloaded_videos.append(video)
                                progress.update(task, completed=100)
                                self.console.print(
                                    f"✅ 下载完成: {downloaded_path.name}",
                                    style="green",
                                )

                                # 翻译字幕（如果启用）
                                if self.translate_subs:
                                    await self.translate_video_subtitles(downloaded_path)
                            else:
                                self.console.print(
                                    f"❌ 下载失败: {video.title}", style="red"
                                )

                        except Exception as e:
                            logger.error(f"下载视频失败: {video.title}, 错误: {str(e)}")
                            self.console.print(
                                f"❌ 下载异常: {video.title}", style="red"
                            )
                            continue
            else:
                for i, video in enumerate(selected_videos):
                    try:
                        print(
                            f"📥 下载中 ({i + 1}/{len(selected_videos)}): {video.title[:50]}..."
                        )

                        downloaded_path = await self.downloader.download_video(video)

                        if downloaded_path:
                            video.downloaded_path = str(downloaded_path)
                            downloaded_videos.append(video)
                            print(f"✅ 下载完成: {downloaded_path.name}")

                            # 翻译字幕（如果启用）
                            if self.translate_subs:
                                await self.translate_video_subtitles(downloaded_path)
                        else:
                            print(f"❌ 下载失败: {video.title}")

                    except Exception as e:
                        logger.error(f"下载视频失败: {video.title}, 错误: {str(e)}")
                        print(f"❌ 下载异常: {video.title}")
                        continue

            self.console.print(
                f"🎉 成功下载 {len(downloaded_videos)} 个视频", style="green"
            )
            return downloaded_videos

        except Exception as e:
            import traceback
            self.console.print(f"❌ 搜索下载失败: {str(e)}", style="red")
            logger.error(f"搜索下载失败: {str(e)}\n{traceback.format_exc()}")
            return []

    def _display_videos(self, videos: List[YouTubeVideo]) -> None:
        """显示视频列表"""
        if not RICH_AVAILABLE:
            print("\n" + "=" * 80)
            print(f"搜索结果 (共{len(videos)}个):")
            print("=" * 80)

            for i, video in enumerate(videos, 1):
                print(f"{i:2d}. {video.title}")
                print(f"     频道: {video.channel_title}")
                print(
                    f"     观看: {(video.view_count or 0):,} | 点赞: {(video.like_count or 0):,} | 评分: {video.get_quality_score():.1f}"
                )
                print(
                    f"     发布: {video.published_at.strftime('%Y-%m-%d')} | 时长: {video._parse_duration_minutes()}分钟"
                )
                print()
        else:
            table = Table(title=f"搜索结果 (共{len(videos)}个)")
            table.add_column("序号", style="cyan", no_wrap=True, width=4)
            table.add_column("标题", style="magenta", width=40)
            table.add_column("频道", style="green", width=20)
            table.add_column("观看/点赞", style="yellow", width=15)
            table.add_column("评分", style="blue", width=6)
            table.add_column("发布时间", style="red", width=10)

            for i, video in enumerate(videos[:20], 1):
                title = (
                    video.title[:37] + "..." if len(video.title) > 40 else video.title
                )
                channel = (
                    video.channel_title[:17] + "..."
                    if len(video.channel_title) > 20
                    else video.channel_title
                )
                views_likes = f"{(video.view_count or 0) // 1000}k/{(video.like_count or 0) // 1000}k"

                table.add_row(
                    str(i),
                    title,
                    channel,
                    views_likes,
                    f"{video.get_quality_score():.1f}",
                    video.published_at.strftime("%m-%d"),
                )

            self.console.print(table)

    def _select_videos(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """选择要下载的视频"""
        try:
            while True:
                if RICH_AVAILABLE:
                    choice = Prompt.ask(
                        "请选择要下载的视频（输入序号，多个用逗号分隔，或输入 'all' 下载全部）",
                        default="1",
                    )
                else:
                    choice = input(
                        "请选择要下载的视频（输入序号，多个用逗号分隔，或输入 'all' 下载全部）[1]: "
                    ).strip()
                    if not choice:
                        choice = "1"

                if choice.lower() == "all":
                    return videos

                try:
                    indices = [int(x.strip()) for x in choice.split(",")]
                    selected = []

                    for idx in indices:
                        if 1 <= idx <= len(videos):
                            selected.append(videos[idx - 1])
                        else:
                            self.console.print(
                                f"❌ 序号 {idx} 超出范围 (1-{len(videos)})", style="red"
                            )
                            break
                    else:
                        if selected:
                            return selected

                except ValueError:
                    self.console.print("❌ 输入格式错误，请输入有效的序号", style="red")

        except (KeyboardInterrupt, EOFError):
            self.console.print("\n取消选择", style="yellow")
            return []

    async def run(self, max_videos: int = 10, upload: bool = False) -> None:
        """运行主程序"""
        try:
            self.console.print(
                "🚀 YouTube to Bilibili 视频搬运工具", style="bold green"
            )
            self.console.print("=" * 50, style="green")

            # 检查配置
            if not self._check_config():
                return

            # 搜索和下载
            videos = await self.search_and_download(max_videos)
            if not videos:
                self.console.print("没有视频可以处理", style="yellow")
                return

            # 显示下载结果
            self._show_download_summary(videos)

            # 上传到B站
            if upload and self.enable_upload:
                await self.upload_to_bilibili(videos)

            self.console.print("🎊 程序执行完成！", style="bold green")

        except KeyboardInterrupt:
            self.console.print("\n程序被用户中断", style="yellow")
        except Exception as e:
            self.console.print(f"❌ 程序执行异常: {str(e)}", style="red")
            logger.error(f"程序执行异常: {str(e)}")

    async def run_by_channel(self, channel_id: str, max_videos: int = 10, upload: bool = False) -> None:
        """根据频道ID运行主程序"""
        try:
            self.console.print(
                "🚀 YouTube to Bilibili 视频搬运工具", style="bold green"
            )
            self.console.print("=" * 50, style="green")

            # 检查配置
            if not self._check_config():
                return

            # 根据频道搜索和下载
            videos = await self.search_and_download_by_channel(channel_id, max_videos)
            if not videos:
                self.console.print("没有视频可以处理", style="yellow")
                return

            # 显示下载结果
            self._show_download_summary(videos)

            # 上传到B站
            if upload and self.enable_upload:
                await self.upload_to_bilibili(videos)

            self.console.print("🎊 程序执行完成！", style="bold green")

        except KeyboardInterrupt:
            self.console.print("\n程序被用户中断", style="yellow")
        except Exception as e:
            self.console.print(f"❌ 程序执行异常: {str(e)}", style="red")
            logger.error(f"程序执行异常: {str(e)}")

    def _check_config(self) -> bool:
        """检查配置"""
        try:
            # 检查必要的目录
            Path(settings.download_path).mkdir(parents=True, exist_ok=True)
            Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)

            self.console.print("✅ 配置检查通过", style="green")

            # 显示配置信息
            self.console.print(f"下载目录: {settings.download_path}")
            self.console.print(f"视频质量: {settings.video_quality}")
            self.console.print(f"最大文件大小: {settings.max_video_size_mb}MB")

            return True

        except Exception as e:
            self.console.print(f"❌ 配置检查失败: {str(e)}", style="red")
            return False

    def _show_download_summary(self, videos: List[YouTubeVideo]) -> None:
        """显示下载摘要"""
        if not videos:
            return

        self.console.print("\n📋 下载摘要:", style="bold blue")

        for i, video in enumerate(videos, 1):
            if hasattr(video, "downloaded_path") and video.downloaded_path:
                path = Path(video.downloaded_path)
                size = path.stat().st_size / (1024 * 1024) if path.exists() else 0
                self.console.print(f"{i}. {video.title[:50]}...")
                self.console.print(f"   文件: {path.name} ({size:.1f}MB)")
            else:
                self.console.print(
                    f"{i}. {video.title[:50]}... [下载失败]", style="red"
                )


    async def search_and_download_by_channel(
        self, channel_id: str, max_videos: int = 10, interactive: bool = False
    ) -> List[YouTubeVideo]:
        """根据频道ID搜索并下载视频"""
        try:
            self.console.print(
                f"🔍 正在获取频道 {channel_id} 的视频...", style="bold blue"
            )

            # 搜索频道视频
            if RICH_AVAILABLE:
                from rich.progress import Progress, SpinnerColumn, TextColumn

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                ) as progress:
                    task = progress.add_task("获取频道视频中...", total=None)
                    videos = await self.searcher.search_by_channel(channel_id, max_videos)
                    progress.update(task, completed=True)
            else:
                print("获取频道视频中...")
                videos = await self.searcher.search_by_channel(channel_id, max_videos)

            if not videos:
                self.console.print("❌ 未找到该频道的视频", style="red")
                return []

            # 非交互模式：直接下载所有视频
            if not interactive:
                self.console.print(f"📋 找到 {len(videos)} 个视频，开始下载...", style="blue")
                return await self._download_videos_direct(videos)

            # 交互模式：显示并选择
            self._display_videos(videos)
            selected_videos = self._select_videos(videos)
            if not selected_videos:
                return []

            return await self._download_videos_direct(selected_videos)

        except Exception as e:
            import traceback
            self.console.print(f"❌ 搜索下载失败: {str(e)}", style="red")
            logger.error(f"搜索下载失败: {str(e)}\n{traceback.format_exc()}")
            return []

    async def _download_videos_direct(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """直接下载视频列表（不交互）"""
        downloaded_videos = []

        if RICH_AVAILABLE:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            ) as progress:
                for i, video in enumerate(videos):
                    task = progress.add_task(
                        f"下载: {video.title[:30]}...", total=100
                    )

                    def update_progress(percent, speed):
                        progress.update(task, completed=percent)

                    try:
                        downloaded_path = await self.downloader.download_video(
                            video, update_progress
                        )

                        if downloaded_path:
                            video.downloaded_path = str(downloaded_path)
                            downloaded_videos.append(video)
                            progress.update(task, completed=100)
                            self.console.print(
                                f"✅ 下载完成: {downloaded_path.name}",
                                style="green",
                            )

                            # 翻译字幕（如果启用）
                            if self.translate_subs:
                                await self.translate_video_subtitles(downloaded_path)
                        else:
                            self.console.print(
                                f"❌ 下载失败: {video.title}", style="red"
                            )

                    except Exception as e:
                        logger.error(f"下载视频失败: {video.title}, 错误: {str(e)}")
                        self.console.print(
                            f"❌ 下载异常: {video.title}", style="red"
                        )
                        continue
        else:
            for i, video in enumerate(videos):
                try:
                    print(
                        f"📥 下载中 ({i + 1}/{len(videos)}): {video.title[:50]}..."
                    )

                    downloaded_path = await self.downloader.download_video(video)

                    if downloaded_path:
                        video.downloaded_path = str(downloaded_path)
                        downloaded_videos.append(video)
                        print(f"✅ 下载完成: {downloaded_path.name}")

                        # 翻译字幕（如果启用）
                        if self.translate_subs:
                            await self.translate_video_subtitles(downloaded_path)
                    else:
                        print(f"❌ 下载失败: {video.title}")

                except Exception as e:
                    logger.error(f"下载视频失败: {video.title}, 错误: {str(e)}")
                    print(f"❌ 下载异常: {video.title}")
                    continue

        self.console.print(
            f"🎉 成功下载 {len(downloaded_videos)} 个视频", style="green"
        )
        return downloaded_videos

    async def upload_to_bilibili(self, videos: List[YouTubeVideo]) -> List:
        """上传视频到B站"""
        if not self.enable_upload or not self.uploader:
            self.console.print("⚠️ 上传功能未启用", style="yellow")
            return []

        upload_results = []

        try:
            self.console.print(f"📤 准备上传 {len(videos)} 个视频到B站...", style="bold blue")

            for i, youtube_video in enumerate(videos):
                if not youtube_video.downloaded_path:
                    self.console.print(
                        f"⚠️ 跳过未下载的视频: {youtube_video.title}", style="yellow"
                    )
                    continue

                try:
                    self.console.print(
                        f"📤 正在上传 ({i + 1}/{len(videos)}): {youtube_video.title[:50]}...",
                        style="blue"
                    )

                    # 优化内容为B站格式
                    bilibili_video = self.content_optimizer.optimize_for_bilibili(
                        youtube_video, youtube_video.downloaded_path
                    )

                    # 上传到B站
                    result = await self.uploader.upload_video(bilibili_video)

                    if result.success:
                        self.console.print(
                            f"✅ 上传成功: {result.bvid} - {result.video_url}",
                            style="green"
                        )
                        upload_results.append(result)
                    else:
                        self.console.print(
                            f"❌ 上传失败: {result.message}",
                            style="red"
                        )
                        upload_results.append(result)

                    # 上传间隔，避免被限流
                    if i < len(videos) - 1:
                        cooldown = settings.upload_cooldown_hours * 3600
                        if cooldown > 0:
                            self.console.print(f"⏰ 等待 {settings.upload_cooldown_hours} 小时后继续...")
                            await asyncio.sleep(cooldown)

                except Exception as e:
                    logger.error(f"上传视频异常: {youtube_video.title}, 错误: {str(e)}")
                    self.console.print(
                        f"❌ 上传异常: {youtube_video.title}",
                        style="red"
                    )
                    continue

            success_count = sum(1 for r in upload_results if r.success)
            self.console.print(
                f"🎊 上传完成: {success_count}/{len(videos)} 成功",
                style="green" if success_count == len(videos) else "yellow"
            )

            return upload_results

        except Exception as e:
            import traceback
            self.console.print(f"❌ 批量上传失败: {str(e)}", style="red")
            logger.error(f"批量上传失败: {str(e)}\n{traceback.format_exc()}")
            return upload_results

    async def translate_video_subtitles(self, video_path: Path) -> Optional[Path]:
        """翻译视频的字幕

        Args:
            video_path: 视频文件路径

        Returns:
            翻译后的字幕文件路径，如果没有字幕或翻译失败则返回None
        """
        try:
            # 查找字幕文件
            subtitle_extensions = [".srt", ".vtt", ".ass"]
            base_name = video_path.stem
            parent_dir = video_path.parent

            subtitle_path = None
            for ext in subtitle_extensions:
                sub_file = parent_dir / f"{base_name}{ext}"
                if sub_file.exists():
                    subtitle_path = sub_file
                    break

            if not subtitle_path:
                logger.info(f"未找到字幕文件: {video_path.name}")
                return None

            self.console.print(f"📝 找到字幕文件: {subtitle_path.name}", style="blue")

            # 只翻译SRT格式的字幕
            if subtitle_path.suffix != ".srt":
                self.console.print(f"⚠️ 字幕格式 {subtitle_path.suffix} 暂不支持自动翻译", style="yellow")
                return None

            # 检查是否已有翻译版本
            translated_path = subtitle_path.parent / f"{base_name}_zh.srt"
            if translated_path.exists():
                self.console.print(f"✅ 翻译字幕已存在: {translated_path.name}", style="green")
                return translated_path

            # 翻译字幕
            self.console.print(f"🌐 正在翻译字幕...", style="blue")
            result = await self.subtitle_processor.translate_with_openai(subtitle_path)

            if result:
                self.console.print(f"✅ 字幕翻译完成: {result.name}", style="green")

                # 如果启用了字幕嵌入，则嵌入双语字幕
                if self.embed_subs:
                    embedded_video = await self.embed_bilingual_subtitles(video_path, result)
                    if embedded_video:
                        self.console.print(f"✅ 双语字幕视频已生成: {embedded_video.name}", style="green")

                return result
            else:
                self.console.print(f"❌ 字幕翻译失败: {subtitle_path.name}", style="red")
                return None

        except Exception as e:
            logger.error(f"翻译字幕异常: {str(e)}")
            self.console.print(f"❌ 字幕翻译异常: {str(e)}", style="red")
            return None

    async def translate_subtitle_file(self, subtitle_path: Path) -> Optional[Path]:
        """翻译独立的字幕文件

        Args:
            subtitle_path: 字幕文件路径

        Returns:
            翻译后的字幕文件路径
        """
        try:
            if not subtitle_path.exists():
                self.console.print(f"❌ 字幕文件不存在: {subtitle_path}", style="red")
                return None

            if subtitle_path.suffix != ".srt":
                self.console.print(f"❌ 仅支持SRT格式字幕", style="red")
                return None

            self.console.print(f"🌐 正在翻译字幕: {subtitle_path.name}", style="blue")

            result = await self.subtitle_processor.translate_with_openai(subtitle_path)

            if result:
                self.console.print(f"✅ 字幕翻译完成: {result.name}", style="green")
                return result
            else:
                self.console.print(f"❌ 字幕翻译失败", style="red")
                return None

        except Exception as e:
            logger.error(f"翻译字幕文件异常: {str(e)}")
            self.console.print(f"❌ 翻译异常: {str(e)}", style="red")
            return None

    async def embed_bilingual_subtitles(self, video_path: Path, translated_subtitle_path: Optional[Path] = None) -> Optional[Path]:
        """将双语字幕嵌入到视频中

        Args:
            video_path: 视频文件路径
            translated_subtitle_path: 翻译后的字幕文件路径，如果为None则自动查找

        Returns:
            嵌入字幕后的视频文件路径，如果失败则返回None
        """
        try:
            # 查找原始字幕
            base_name = video_path.stem
            parent_dir = video_path.parent
            original_subtitle_path = parent_dir / f"{base_name}.srt"

            if not original_subtitle_path.exists():
                self.console.print(f"⚠️ 未找到原始字幕文件: {original_subtitle_path.name}", style="yellow")
                return None

            # 如果未提供翻译字幕路径，尝试查找
            if translated_subtitle_path is None:
                translated_subtitle_path = parent_dir / f"{base_name}_zh.srt"

            if not translated_subtitle_path.exists():
                self.console.print(f"⚠️ 未找到翻译字幕文件: {translated_subtitle_path.name}", style="yellow")
                return None

            self.console.print(f"📝 正在合并双语字幕...", style="blue")

            # 合并双语字幕
            bilingual_subtitle_path = self.subtitle_processor.merge_bilingual_srt(
                original_subtitle_path, translated_subtitle_path
            )
            self.console.print(f"✅ 双语字幕合并完成: {bilingual_subtitle_path.name}", style="green")

            # 检查是否已有嵌入字幕的视频
            embedded_video_path = parent_dir / f"{base_name}_embedded{video_path.suffix}"
            if embedded_video_path.exists():
                self.console.print(f"✅ 嵌入字幕的视频已存在: {embedded_video_path.name}", style="green")
                return embedded_video_path

            self.console.print(f"🎬 正在将字幕嵌入视频...", style="blue")

            # 嵌入字幕到视频
            result_path = await self.subtitle_processor.embed_subtitles_to_video(
                video_path, bilingual_subtitle_path
            )

            self.console.print(f"✅ 字幕嵌入完成: {result_path.name}", style="green")
            return result_path

        except Exception as e:
            logger.error(f"嵌入字幕异常: {str(e)}")
            self.console.print(f"❌ 嵌入字幕异常: {str(e)}", style="red")
            return None

    async def embed_bilingual_subtitles_standalone(self, video_path: Path, en_subs_path: Path, zh_subs_path: Path) -> None:
        """独立的双语字幕嵌入功能

        Args:
            video_path: 视频文件路径
            en_subs_path: 英文字幕文件路径
            zh_subs_path: 中文字幕文件路径
        """
        try:
            self.console.print("🚀 双语字幕嵌入工具", style="bold green")
            self.console.print("=" * 50, style="green")

            # 验证输入文件
            if not video_path.exists():
                self.console.print(f"❌ 视频文件不存在: {video_path}", style="red")
                return

            if not en_subs_path.exists():
                self.console.print(f"❌ 英文字幕文件不存在: {en_subs_path}", style="red")
                return

            if not zh_subs_path.exists():
                self.console.print(f"❌ 中文字幕文件不存在: {zh_subs_path}", style="red")
                return

            self.console.print(f"📹 视频: {video_path.name}", style="blue")
            self.console.print(f"📝 英文字幕: {en_subs_path.name}", style="blue")
            self.console.print(f"📝 中文字幕: {zh_subs_path.name}", style="blue")

            # 步骤1: 合并双语字幕
            self.console.print(f"\n📝 步骤 1/2: 合并双语字幕...", style="bold blue")

            bilingual_subtitle_path = self.subtitle_processor.merge_bilingual_srt(
                en_subs_path, zh_subs_path
            )

            self.console.print(f"✅ 双语字幕已生成: {bilingual_subtitle_path}", style="green")

            # 步骤2: 嵌入字幕到视频
            self.console.print(f"\n🎬 步骤 2/2: 嵌入字幕到视频...", style="bold blue")

            embedded_video_path = await self.subtitle_processor.embed_subtitles_to_video(
                video_path, bilingual_subtitle_path
            )

            self.console.print(f"✅ 嵌入字幕视频已生成: {embedded_video_path}", style="green")

            # 显示输出摘要
            self.console.print(f"\n📊 输出文件:", style="bold green")
            self.console.print(f"  1. 双语字幕: {bilingual_subtitle_path}")
            self.console.print(f"  2. 嵌入字幕视频: {embedded_video_path}")

            # 显示文件大小
            bilingual_size = bilingual_subtitle_path.stat().st_size / 1024  # KB
            video_size = embedded_video_path.stat().st_size / (1024 * 1024)  # MB
            self.console.print(f"\n📁 文件大小:")
            self.console.print(f"  - 双语字幕: {bilingual_size:.1f} KB")
            self.console.print(f"  - 嵌入字幕视频: {video_size:.1f} MB")

            self.console.print(f"\n🎊 处理完成！", style="bold green")

        except Exception as e:
            logger.error(f"双语字幕嵌入失败: {str(e)}")
            self.console.print(f"❌ 处理失败: {str(e)}", style="red")
            import traceback
            logger.error(traceback.format_exc())

    def scan_local_videos(self) -> List[LocalVideo]:
        """扫描data目录中的本地视频"""
        try:
            download_path = Path(settings.download_path)
            if not download_path.exists():
                self.console.print(f"❌ 下载目录不存在: {download_path}", style="red")
                return []

            # 支持的视频扩展名
            video_extensions = [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"]

            local_videos = []
            for ext in video_extensions:
                for filepath in download_path.glob(f"*{ext}"):
                    local_video = LocalVideo(filepath)
                    # 包含所有视频文件（无论是否有video_id）
                    local_videos.append(local_video)

            # 按文件修改时间排序（最新的在前）
            local_videos.sort(key=lambda v: v.filepath.stat().st_mtime, reverse=True)

            return local_videos

        except Exception as e:
            logger.error(f"扫描本地视频失败: {str(e)}")
            return []

    def _display_local_videos(self, local_videos: List[LocalVideo]) -> None:
        """显示本地视频列表"""
        if not RICH_AVAILABLE:
            print("\n" + "=" * 80)
            print(f"本地视频 (共{len(local_videos)}个):")
            print("=" * 80)

            for i, lv in enumerate(local_videos, 1):
                print(f"{i:2d}. {lv.filename}")
                print(f"     大小: {lv.filesize_mb:.1f}MB | ID: {lv.video_id}")
                print()
        else:
            table = Table(title=f"本地视频 (共{len(local_videos)}个)")
            table.add_column("序号", style="cyan", no_wrap=True, width=4)
            table.add_column("文件名", style="magenta", width=50)
            table.add_column("大小(MB)", style="yellow", width=10)
            table.add_column("视频ID", style="blue", width=14)

            for i, lv in enumerate(local_videos, 1):
                filename = lv.filename[:47] + "..." if len(lv.filename) > 50 else lv.filename
                table.add_row(
                    str(i),
                    filename,
                    f"{lv.filesize_mb:.1f}",
                    lv.video_id or "未知"
                )

            self.console.print(table)

    async def fetch_youtube_info_for_local(self, local_videos: List[LocalVideo]) -> None:
        """为本地视频获取YouTube信息"""
        if not RICH_AVAILABLE:
            print("正在获取视频信息...")
            for lv in local_videos:
                if lv.video_id:
                    try:
                        url = f"https://www.youtube.com/watch?v={lv.video_id}"
                        info = await self.downloader.get_video_info(url)
                        lv.youtube_info = info
                    except Exception as e:
                        logger.debug(f"获取视频信息失败 {lv.video_id}: {str(e)}")
                else:
                    logger.debug(f"跳过无video_id的视频: {lv.filename}")
        else:
            from rich.progress import Progress, SpinnerColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task("获取YouTube信息...", total=len(local_videos))
                for lv in local_videos:
                    if lv.video_id:
                        try:
                            url = f"https://www.youtube.com/watch?v={lv.video_id}"
                            info = await self.downloader.get_video_info(url)
                            lv.youtube_info = info
                        except Exception as e:
                            logger.debug(f"获取视频信息失败 {lv.video_id}: {str(e)}")
                    else:
                        logger.debug(f"跳过无video_id的视频: {lv.filename}")
                    progress.advance(task)

    def _select_local_videos(self, local_videos: List[LocalVideo]) -> List[LocalVideo]:
        """选择要上传的本地视频"""
        try:
            while True:
                if RICH_AVAILABLE:
                    choice = Prompt.ask(
                        "请选择要上传的视频（输入序号，多个用逗号分隔，或输入 'all' 上传全部）",
                        default="1",
                    )
                else:
                    choice = input(
                        "请选择要上传的视频（输入序号，多个用逗号分隔，或输入 'all' 上传全部）[1]: "
                    ).strip()
                    if not choice:
                        choice = "1"

                if choice.lower() == "all":
                    return local_videos

                try:
                    indices = [int(x.strip()) for x in choice.split(",")]
                    selected = []

                    for idx in indices:
                        if 1 <= idx <= len(local_videos):
                            selected.append(local_videos[idx - 1])
                        else:
                            self.console.print(
                                f"❌ 序号 {idx} 超出范围 (1-{len(local_videos)})", style="red"
                            )
                            break
                    else:
                        if selected:
                            return selected

                except ValueError:
                    self.console.print("❌ 输入格式错误，请输入有效的序号", style="red")

        except (KeyboardInterrupt, EOFError):
            self.console.print("\n取消选择", style="yellow")
            return []

    async def upload_local_videos(self, local_videos: List[LocalVideo]) -> List:
        """上传本地视频到B站"""
        if not self.enable_upload or not self.uploader:
            self.console.print("⚠️ 上传功能未启用，请使用 --upload 参数", style="yellow")
            return []

        # 模拟模式
        if self.dry_run:
            self.console.print("🧪 模拟模式：将会上传以下视频（不实际上传）", style="yellow")
            for i, local_video in enumerate(local_videos):
                self.console.print(f"  {i + 1}. {local_video.filename} ({local_video.filesize_mb:.1f}MB)")
            return []

        upload_results = []

        try:
            self.console.print(f"📤 准备上传 {len(local_videos)} 个本地视频到B站...", style="bold blue")

            for i, local_video in enumerate(local_videos):
                try:
                    self.console.print(
                        f"📤 正在上传 ({i + 1}/{len(local_videos)}): {local_video.filename[:50]}...",
                        style="blue"
                    )

                    # 使用YouTube信息或使用文件名作为标题
                    if local_video.youtube_info:
                        youtube_video = local_video.youtube_info
                    else:
                        # 创建基本的YouTubeVideo对象
                        youtube_video = YouTubeVideo(
                            video_id=local_video.video_id or "",
                            title=local_video.title,
                            description=f"从本地文件上传: {local_video.filename}",
                            channel_title="Unknown",
                            channel_id="",
                            published_at=datetime.now(),
                        )

                    youtube_video.downloaded_path = str(local_video.filepath)

                    # 翻译字幕（如果启用）
                    if self.translate_subs:
                        await self.translate_video_subtitles(local_video.filepath)

                    # 优化内容为B站格式
                    bilibili_video = self.content_optimizer.optimize_for_bilibili(
                        youtube_video, youtube_video.downloaded_path
                    )

                    # 上传到B站
                    result = await self.uploader.upload_video(bilibili_video)

                    if result.success:
                        self.console.print(
                            f"✅ 上传成功: {result.bvid} - {result.video_url}",
                            style="green"
                        )
                        upload_results.append(result)
                    else:
                        self.console.print(
                            f"❌ 上传失败: {result.message}",
                            style="red"
                        )
                        upload_results.append(result)

                    # 上传间隔，避免被限流
                    if i < len(local_videos) - 1:
                        cooldown = settings.upload_cooldown_hours * 3600
                        if cooldown > 0:
                            self.console.print(f"⏰ 等待 {settings.upload_cooldown_hours} 小时后继续...")
                            await asyncio.sleep(cooldown)

                except Exception as e:
                    logger.error(f"上传视频异常: {local_video.filename}, 错误: {str(e)}")
                    self.console.print(
                        f"❌ 上传异常: {local_video.filename}",
                        style="red"
                    )
                    continue

            success_count = sum(1 for r in upload_results if r.success)
            self.console.print(
                f"🎊 上传完成: {success_count}/{len(local_videos)} 成功",
                style="green" if success_count == len(local_videos) else "yellow"
            )

            return upload_results

        except Exception as e:
            import traceback
            self.console.print(f"❌ 批量上传失败: {str(e)}", style="red")
            logger.error(f"批量上传失败: {str(e)}\n{traceback.format_exc()}")
            return upload_results

    async def run_upload_local(self, filename: Optional[str] = None, upload_all: bool = False) -> None:
        """运行上传本地视频流程"""
        try:
            self.console.print(
                "🚀 本地视频上传到B站", style="bold green"
            )
            self.console.print("=" * 50, style="green")

            # 检查配置
            if not self._check_config():
                return

            # 如果指定了文件名，直接上传该视频
            if filename:
                download_path = Path(settings.download_path)
                video_path = download_path / filename

                if not video_path.exists():
                    # 尝试添加常见扩展名
                    for ext in [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"]:
                        test_path = download_path / (filename + ext)
                        if test_path.exists():
                            video_path = test_path
                            break

                if not video_path.exists():
                    self.console.print(f"❌ 未找到视频文件: {filename}", style="red")
                    return

                local_video = LocalVideo(video_path)

                # 获取YouTube信息（如果有video_id）
                if local_video.video_id:
                    self.console.print("📡 正在获取YouTube视频信息...", style="blue")
                    try:
                        url = f"https://www.youtube.com/watch?v={local_video.video_id}"
                        info = await self.downloader.get_video_info(url)
                        local_video.youtube_info = info
                    except Exception as e:
                        logger.debug(f"获取视频信息失败: {str(e)}")

                # 上传到B站
                await self.upload_local_videos([local_video])
            elif upload_all:
                # 上传所有视频
                local_videos = self.scan_local_videos()
                if not local_videos:
                    self.console.print("❌ 未找到本地视频", style="yellow")
                    return

                self.console.print(f"📋 找到 {len(local_videos)} 个视频，准备上传", style="blue")

                # 获取YouTube信息
                self.console.print("📡 正在获取YouTube视频信息...", style="blue")
                await self.fetch_youtube_info_for_local(local_videos)

                # 上传到B站
                await self.upload_local_videos(local_videos)
            else:
                # 未指定文件名，扫描并显示所有视频
                local_videos = self.scan_local_videos()
                if not local_videos:
                    self.console.print("❌ 未找到本地视频", style="yellow")
                    return

                # 显示视频列表
                self._display_local_videos(local_videos)

                # 获取YouTube信息
                self.console.print("📡 正在获取YouTube视频信息...", style="blue")
                await self.fetch_youtube_info_for_local(local_videos)

                # 显示获取到的信息
                if RICH_AVAILABLE:
                    from rich.table import Table
                    table = Table(title="视频详细信息")
                    table.add_column("序号", style="cyan", width=4)
                    table.add_column("标题", style="magenta", width=40)
                    table.add_column("频道", style="green", width=20)

                    for i, lv in enumerate(local_videos[:20], 1):
                        if lv.youtube_info:
                            title = lv.youtube_info.title[:37] + "..." if len(lv.youtube_info.title) > 40 else lv.youtube_info.title
                            channel = lv.youtube_info.channel_title[:17] + "..." if len(lv.youtube_info.channel_title) > 20 else lv.youtube_info.channel_title
                            table.add_row(str(i), title, channel)
                        else:
                            table.add_row(str(i), "(无法获取信息)", "-")

                    self.console.print(table)

                # 选择要上传的视频
                selected_videos = self._select_local_videos(local_videos)
                if not selected_videos:
                    self.console.print("未选择任何视频", style="yellow")
                    return

                # 上传到B站
                await self.upload_local_videos(selected_videos)

            self.console.print("🎊 程序执行完成！", style="bold green")

        except KeyboardInterrupt:
            self.console.print("\n程序被用户中断", style="yellow")
        except Exception as e:
            self.console.print(f"❌ 程序执行异常: {str(e)}", style="red")
            logger.error(f"程序执行异常: {str(e)}")

    def read_author_file(self, filepath: str) -> List[tuple]:
        """读取作者配置文件

        Args:
            filepath: 作者配置文件路径

        Returns:
            [(作者名, 最大视频数), ...] 列表
        """
        try:
            authors = []
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过空行和注释行
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('\t')
                    if len(parts) != 2:
                        logger.warning(f"文件格式错误（第{line_num}行）: {line}")
                        continue

                    name, max_num = parts
                    try:
                        max_num = int(max_num)
                        authors.append((name, max_num))
                    except ValueError:
                        logger.warning(f"视频数量格式错误（第{line_num}行）: {max_num}")
                        continue

            return authors

        except FileNotFoundError:
            logger.error(f"文件不存在: {filepath}")
            return []
        except Exception as e:
            logger.error(f"读取文件失败: {str(e)}")
            return []

    async def run_batch_download(self, author_file: str, upload: bool = False) -> None:
        """根据作者文件批量下载视频

        Args:
            author_file: 作者配置文件路径
            upload: 是否上传到B站
        """
        try:
            self.console.print(
                "🚀 批量下载作者视频", style="bold green"
            )
            self.console.print("=" * 50, style="green")

            # 检查配置
            if not self._check_config():
                return

            # 读取作者文件
            authors = self.read_author_file(author_file)
            if not authors:
                self.console.print(f"❌ 未找到有效的作者配置", style="red")
                return

            self.console.print(f"📋 找到 {len(authors)} 个作者配置", style="blue")

            # 遍历每个作者
            all_downloaded = []
            for i, (author_name, max_videos) in enumerate(authors, 1):
                self.console.print(f"\n[{i}/{len(authors)}] 处理作者: {author_name} (最多{max_videos}个视频)", style="cyan")

                # 下载该作者的视频
                videos = await self.search_and_download_by_channel(author_name, max_videos)
                if videos:
                    all_downloaded.extend(videos)
                    self.console.print(f"✅ 成功下载 {len(videos)} 个视频", style="green")
                else:
                    self.console.print(f"⚠️ 该作者未下载到视频", style="yellow")

            # 显示汇总
            self.console.print(f"\n📊 总共下载 {len(all_downloaded)} 个视频", style="bold green")

            # 上传到B站
            if upload and self.enable_upload and all_downloaded:
                await self.upload_to_bilibili(all_downloaded)

            self.console.print("🎊 程序执行完成！", style="bold green")

        except KeyboardInterrupt:
            self.console.print("\n程序被用户中断", style="yellow")
        except Exception as e:
            self.console.print(f"❌ 程序执行异常: {str(e)}", style="red")
            logger.error(f"程序执行异常: {str(e)}")


# CLI入口点
def cli() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(description="YouTube到B站视频搬运工具")
    parser.add_argument("--max-videos", type=int, default=10, help="最大处理视频数量")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--url", type=str, help="下载指定URL的视频")
    parser.add_argument("--channel-id", type=str, help="下载指定频道的视频 (支持: @username, UC...ID, 或完整URL)")
    parser.add_argument("--upload", action="store_true", help="下载后自动上传到B站")
    parser.add_argument("--upload-local", nargs="?", const="", metavar="FILENAME", help="上传本地视频到B站 (可指定文件名，不指定则显示列表)")
    parser.add_argument("--all", action="store_true", help="上传data目录内所有视频 (需配合--upload-local使用)")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式，不实际上传（用于测试）")
    parser.add_argument("--batch", metavar="AUTHOR_FILE", help="根据作者文件批量下载 (scripts/author_videonum.txt)")
    parser.add_argument("--translate", action="store_true", help="下载/上传时自动翻译字幕为中文")
    parser.add_argument("--translate-subs", metavar="SUBTITLE_FILE", help="翻译指定的字幕文件（独立功能）")
    parser.add_argument("--embed-subs", action="store_true", help="翻译后将双语字幕嵌入到视频中（需配合--translate使用）")
    parser.add_argument("--embed-bilingual", nargs=3, metavar=("VIDEO", "EN_SUBS", "ZH_SUBS"),
                        help="嵌入双语字幕到视频: 视频文件 英文字幕 中文字幕")

    args = parser.parse_args()

    # 运行主程序
    app = YouTubeToBilibili(
        enable_upload=args.upload or args.upload_local is not None,
        dry_run=args.dry_run,
        translate_subs=args.translate,
        embed_subs=args.embed_subs
    )

    # 独立双语字幕嵌入功能
    if args.embed_bilingual:
        video_path = Path(args.embed_bilingual[0])
        en_subs_path = Path(args.embed_bilingual[1])
        zh_subs_path = Path(args.embed_bilingual[2])
        asyncio.run(app.embed_bilingual_subtitles_standalone(video_path, en_subs_path, zh_subs_path))
        return

    # 独立字幕翻译功能
    if args.translate_subs:
        subtitle_path = Path(args.translate_subs)
        asyncio.run(app.translate_subtitle_file(subtitle_path))
        return

    if args.batch:
        # 批量下载
        asyncio.run(app.run_batch_download(args.batch, upload=args.upload))
    elif args.upload_local is not None:
        # 上传本地视频
        filename = args.upload_local if args.upload_local else None
        asyncio.run(app.run_upload_local(filename, upload_all=args.all))
    elif args.url:
        # 下载单个视频
        async def download_single():
            video = await app.downloader.get_video_info(args.url)
            if video:
                downloaded = await app.downloader.download_video(video)
                if downloaded:
                    print(f"✅ 下载完成: {downloaded}")
                    # 如果启用上传，则上传到B站
                    if args.upload:
                        video.downloaded_path = str(downloaded)
                        await app.upload_to_bilibili([video])
                else:
                    print("❌ 下载失败")
            else:
                print("❌ 无法获取视频信息")

        asyncio.run(download_single())
    elif args.channel_id:
        # 根据频道ID下载
        asyncio.run(app.run_by_channel(args.channel_id, args.max_videos, upload=args.upload))
    else:
        # 运行完整流程（搜索热门视频）
        asyncio.run(app.run(args.max_videos, upload=args.upload))


if __name__ == "__main__":
    cli()
