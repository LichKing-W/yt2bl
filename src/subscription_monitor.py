"""YouTube订阅监控器

定期检查YouTube订阅频道的新视频，自动下载并上传到B站
推荐使用 crontab 定时运行此脚本
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import argparse
import sys

from .utils.logger import logger
from .utils.config import settings
from .youtube.searcher import YouTubeSearcher
from .youtube.models import YouTubeVideo
from .main import YouTubeToBilibili

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class SubscriptionMonitor:
    """YouTube订阅监控器

    功能：
    1. 从 youtuber.txt 读取YouTuber列表
    2. 检查每个频道的新视频（最近3条）
    3. 与历史记录对比，找出未处理的视频
    4. 使用 full-workflow 处理视频（下载、翻译、嵌入字幕、上传）
    5. 失败重试一次，再失败则跳过
    """

    # 历史记录文件路径
    HISTORY_FILE = Path("subscription_history.json")

    # YouTuber列表文件
    YOUTUBERS_FILE = Path("youtuber.txt")

    # 更新标记文件
    UPDATING_FILE = Path(".updating")

    # 每个频道获取的最新视频数量
    VIDEOS_PER_CHANNEL = 3

    def __init__(
        self,
        translate_subs: bool = True,
        embed_subs: bool = True,
    ):
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

        self.searcher = YouTubeSearcher()

        # 创建 YouTubeToBilibili 实例用于处理视频
        self.yt2bl = YouTubeToBilibili(
            enable_upload=True,
            dry_run=False,
            translate_subs=translate_subs,
            embed_subs=embed_subs,
        )

        # 加载历史记录
        self.processed_videos: Set[str] = self._load_history()

    def _load_history(self) -> Set[str]:
        """从文件加载已处理视频ID集合"""
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    processed = set(data.get("processed_videos", []))
                    logger.info(f"成功加载历史记录: {len(processed)} 个已处理视频")
                    return processed
            except json.JSONDecodeError as e:
                logger.error(f"历史记录文件JSON格式错误: {e}")
                logger.error(f"错误位置: 第{e.lineno}行, 第{e.colno}列")
                logger.error(f"请修复 {self.HISTORY_FILE} 文件的JSON格式")
                # 尝试备份损坏的文件
                backup_path = self.HISTORY_FILE.with_suffix(".json.corrupted")
                try:
                    import shutil
                    shutil.copy(self.HISTORY_FILE, backup_path)
                    logger.info(f"已将损坏的文件备份到 {backup_path}")
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"加载历史记录失败: {e}")
        else:
            logger.info("历史记录文件不存在，将创建新文件")
        return set()

    def _save_history(self):
        """保存已处理视频ID到文件"""
        try:
            self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "processed_videos": list(self.processed_videos),
                    "last_updated": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")

    def _add_to_history(self, video_id: str):
        """添加视频到历史记录"""
        self.processed_videos.add(video_id)
        self._save_history()

    def _load_youtubers_list(self) -> List[Dict[str, Any]]:
        """从文件加载YouTuber列表

        文件格式：每行一个YouTuber，支持：
        - @username (频道handle)
        - UCxxxxxxxxxxxxxxxxxx (频道ID)
        - https://www.youtube.com/@username
        - https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxx
        """
        youtubers = []

        if not self.YOUTUBERS_FILE.exists():
            logger.warning(f"YouTuber列表文件不存在: {self.YOUTUBERS_FILE}")
            logger.warning("请创建youtuber.txt文件，每行一个YouTuber（支持 @username 或 UC...ID 格式）")
            return youtubers

        try:
            with open(self.YOUTUBERS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith("#"):
                        continue

                    # 提取频道标识符
                    channel_id = self._extract_channel_identifier(line)
                    if channel_id:
                        youtubers.append({
                            "channel_id": channel_id,
                            "title": channel_id,  # 标题后续会更新
                            "url": line,
                        })

            logger.info(f"从 {self.YOUTUBERS_FILE} 加载了 {len(youtubers)} 个YouTuber")
        except Exception as e:
            logger.error(f"加载YouTuber列表失败: {e}")

        return youtubers

    def _extract_channel_identifier(self, line: str) -> Optional[str]:
        """从行中提取频道标识符"""
        import re

        # 如果是URL，提取频道部分
        if line.startswith("http"):
            patterns = [
                r"/@([\w-]+)",  # @username
                r"/channel/(UC[\w-]+)",  # /channel/UC...
                r"/c/([\w-]+)",  # /c/username
                r"/user/([\w-]+)",  # /user/username
            ]
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    identifier = match.group(1)
                    # 如果不是以UC开头的频道ID，添加@前缀
                    if not identifier.startswith("UC"):
                        return f"@{identifier}"
                    return identifier
            return None

        # 如果已经是@username格式，直接返回
        if line.startswith("@"):
            return line

        # 如果是UC开头的频道ID，直接返回
        if line.startswith("UC"):
            return line

        # 否则当作username处理，添加@前缀
        return f"@{line}"

    async def get_youtubers(self) -> List[Dict[str, Any]]:
        """获取YouTuber列表（从文件读取）"""
        logger.info("正在读取YouTuber列表...")
        youtubers = self._load_youtubers_list()

        if self.console:
            self.console.print(f"✅ 获取到 [green]{len(youtubers)}[/green] 个YouTuber")
        else:
            print(f"✅ 获取到 {len(youtubers)} 个YouTuber")

        return youtubers

    async def check_new_videos(self, youtubers: List[Dict[str, Any]]) -> List[YouTubeVideo]:
        """检查所有YouTuber的新视频

        Args:
            youtubers: YouTuber列表

        Returns:
            新视频列表（未在历史记录中的）
        """
        new_videos = []

        for youtuber in youtubers:
            channel_id = youtuber.get("channel_id", "")
            channel_title = youtuber.get("title", "Unknown")

            if not channel_id:
                continue

            try:
                logger.info(f"检查频道: {channel_title}")

                # 获取频道最近视频
                videos = await self.searcher.search_by_channel(
                    channel_id,
                    max_results=self.VIDEOS_PER_CHANNEL,
                    order="date"
                )

                # 筛选出未处理的视频
                unprocessed_videos = [
                    video for video in videos
                    if video.video_id not in self.processed_videos
                ]

                # 处理所有新视频
                for video in unprocessed_videos:
                    new_videos.append(video)
                    logger.info(f"  发现新视频: {video.title}")

            except Exception as e:
                logger.error(f"检查频道 {channel_title} 失败: {e}")
                continue

        if self.console:
            self.console.print(f"✅ 共发现 [green]{len(new_videos)}[/green] 个新视频")
        else:
            print(f"✅ 共发现 {len(new_videos)} 个新视频")

        return new_videos

    async def process_video(self, video: YouTubeVideo, retry: bool = False) -> bool:
        """处理单个视频 - 使用 full workflow

        Args:
            video: 视频信息
            retry: 是否为重试

        Returns:
            是否成功
        """
        prefix = "重试" if retry else "处理"

        if self.console:
            self.console.print(f"\n{'='*60}")
            self.console.print(f"{prefix}视频: [cyan]{video.title}[/cyan]")
            self.console.print(f"频道: {video.channel_title}")
            self.console.print(f"URL: {video.url}")
            self.console.print(f"[dim]使用 full-workflow 模式处理[/dim]")
        else:
            print(f"\n{'='*60}")
            print(f"{prefix}视频: {video.title}")
            print(f"频道: {video.channel_title}")
            print(f"URL: {video.url}")
            print("使用 full-workflow 模式处理")

        try:
            # 使用 full workflow 处理视频
            # 上传成功后会自动添加到历史记录
            await self.yt2bl.run_full_workflow(video.url)

            if self.console:
                self.console.print(f"[green]✓[/green] {prefix}完成！")
            else:
                print(f"✓ {prefix}完成！")

            return True

        except Exception as e:
            if self.console:
                self.console.print(f"[red]✗[/red] {prefix}失败: {e}")
            else:
                print(f"✗ {prefix}失败: {e}")
            logger.error(f"{prefix}视频失败 {video.video_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def process_queue(self, videos: List[YouTubeVideo]):
        """处理视频队列

        失败重试一次，再失败则跳过
        """
        total = len(videos)

        for i, video in enumerate(videos, 1):
            if self.console:
                self.console.print(f"\n[bold cyan]进度: {i}/{total}[/bold cyan]")
            else:
                print(f"\n进度: {i}/{total}")

            # 首次尝试
            success = await self.process_video(video)

            # 失败则重试一次
            if not success:
                if self.console:
                    self.console.print(f"[yellow]等待5秒后重试...[/yellow]")
                else:
                    print("等待5秒后重试...")
                await asyncio.sleep(5)

                success = await self.process_video(video, retry=True)

                # 重试仍然失败
                if not success:
                    if self.console:
                        self.console.print(f"[red]✗[/red] 视频 [cyan]{video.title}[/cyan] 处理失败，跳过")
                    else:
                        print(f"✗ 视频 {video.title} 处理失败，跳过")
                    continue

        if self.console:
            self.console.print(f"\n[bold green]✓ 队列处理完成！[/bold green]")
        else:
            print("\n✓ 队列处理完成！")

    async def run_once(self):
        """运行一次检查流程"""
        # 检查是否有其他实例正在运行
        if self.UPDATING_FILE.exists():
            logger.warning("检测到其他监控实例正在运行，本次运行取消")
            if self.console:
                self.console.print("[yellow]⚠ 检测到其他监控实例正在运行，本次运行取消[/yellow]")
            else:
                print("⚠ 检测到其他监控实例正在运行，本次运行取消")
            return

        # 创建更新标记文件
        try:
            import os
            pid = os.getpid()
            start_time = datetime.now().isoformat()
            self.UPDATING_FILE.write_text(f"PID: {pid}\nStarted: {start_time}\n")
            logger.info(f"创建更新标记文件: {self.UPDATING_FILE}")
        except Exception as e:
            logger.error(f"创建更新标记文件失败: {e}")
            # 即使创建失败也继续运行

        try:
            # 1. 获取YouTuber列表
            youtubers = await self.get_youtubers()
            if not youtubers:
                logger.warning("未获取到YouTuber列表，请检查youtuber.txt配置")
                return

            # 2. 检查新视频
            new_videos = await self.check_new_videos(youtubers)

            if not new_videos:
                if self.console:
                    self.console.print("[yellow]未发现新视频[/yellow]")
                else:
                    print("未发现新视频")
                return

            # 3. 处理队列
            await self.process_queue(new_videos)

        except Exception as e:
            logger.error(f"监控流程出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 无论成功还是失败，都删除更新标记文件
            try:
                if self.UPDATING_FILE.exists():
                    self.UPDATING_FILE.unlink()
                    logger.info(f"删除更新标记文件: {self.UPDATING_FILE}")
            except Exception as e:
                logger.error(f"删除更新标记文件失败: {e}")


def run(
    translate_subs: bool = True,
    embed_subs: bool = True,
):
    """运行订阅监控（同步入口）"""
    monitor = SubscriptionMonitor(
        translate_subs=translate_subs,
        embed_subs=embed_subs,
    )
    asyncio.run(monitor.run_once())


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="YouTube订阅监控器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 crontab 定时运行（推荐）
  crontab -e

  # 每小时运行一次
  0 * * * * cd /path/to/yt2bl && python -m src.subscription_monitor

  # 每30分钟运行一次
  */30 * * * * cd /path/to/yt2bl && python -m src.subscription_monitor

  # 测试运行（不翻译字幕）
  python -m src.subscription_monitor --no-translate
        """
    )

    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="不翻译字幕"
    )

    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="不嵌入字幕"
    )

    args = parser.parse_args()

    run(
        translate_subs=not args.no_translate,
        embed_subs=not args.no_embed,
    )


if __name__ == "__main__":
    main()
