"""视频处理和转码模块"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
import tempfile
import json

from ..utils.logger import logger
from ..utils.config import settings


class VideoProcessor:
    """视频处理器"""

    def __init__(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / "youtube_to_bilibili"
        self.temp_dir.mkdir(exist_ok=True)

    async def process_video(self, video_path: Path) -> Optional[Path]:
        """处理视频文件"""
        try:
            logger.info(f"开始处理视频: {video_path}")

            # 检查文件是否存在
            if not video_path.exists():
                logger.error(f"视频文件不存在: {video_path}")
                return None

            # 获取视频信息
            video_info = await self.get_video_info(video_path)
            if not video_info:
                logger.error("无法获取视频信息")
                return None

            # 检查文件大小
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_video_size_mb:
                logger.warning(f"视频文件过大 ({file_size_mb:.1f}MB)，开始压缩...")
                compressed_path = await self.compress_video(video_path)
                if compressed_path:
                    video_path = compressed_path
                else:
                    logger.error("视频压缩失败")
                    return None

            # 优化视频格式为B站友好的格式
            optimized_path = await self.optimize_for_bilibili(video_path)
            if optimized_path:
                logger.info(f"视频处理完成: {optimized_path}")
                return optimized_path
            else:
                logger.error("视频优化失败")
                return None

        except Exception as e:
            logger.error(f"视频处理失败: {str(e)}")
            return None

    async def get_video_info(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """获取视频信息"""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return json.loads(stdout.decode("utf-8"))
            else:
                logger.error(f"ffprobe执行失败: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")
            return None

    async def compress_video(
        self, video_path: Path, target_size_mb: Optional[int] = None
    ) -> Optional[Path]:
        """压缩视频"""
        try:
            if target_size_mb is None:
                target_size_mb = settings.max_video_size_mb * 0.8  # 留一些余量

            # 计算目标比特率
            target_size_bytes = target_size_mb * 1024 * 1024
            video_info = await self.get_video_info(video_path)

            if not video_info:
                return None

            # 获取视频时长
            duration = float(video_info["format"].get("duration", 0))
            if duration <= 0:
                logger.error("无法获取视频时长")
                return None

            # 计算目标比特率 (字节/秒 * 8 / 1024 = kbps)
            target_bitrate = int((target_size_bytes * 0.9) / duration * 8 / 1024)

            output_path = self.temp_dir / f"compressed_{video_path.stem}.mp4"

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-maxrate",
                f"{target_bitrate}k",
                "-bufsize",
                f"{target_bitrate * 2}k",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",  # 优化网络播放
                "-y",  # 覆盖输出文件
                str(output_path),
            ]

            logger.info(f"开始压缩视频，目标大小: {target_size_mb}MB")

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and output_path.exists():
                actual_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"视频压缩完成，实际大小: {actual_size_mb:.1f}MB")
                return output_path
            else:
                logger.error(f"视频压缩失败: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"视频压缩异常: {str(e)}")
            return None

    async def optimize_for_bilibili(self, video_path: Path) -> Optional[Path]:
        """为B站优化视频格式"""
        try:
            # B站推荐的视频参数
            # - 分辨率: 最大1920x1080
            # - 编码: H.264 (AVC)
            # - 帧率: 建议30fps
            # - 码率: 根据分辨率调整

            output_path = self.temp_dir / f"bilibili_{video_path.stem}.mp4"

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                # 视频编码器设置
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",  # 质量设置
                "-profile:v",
                "high",
                "-level",
                "4.2",
                # 分辨率限制
                "-vf",
                "scale=if(gt(iw,1920),1920,-1):if(gt(ih,1080),-1,1080)",
                # 帧率限制
                "-r",
                "30",
                # 音频编码器设置
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "44100",
                # 优化设置
                "-movflags",
                "+faststart",
                "-pix_fmt",
                "yuv420p",  # 确保兼容性
                "-y",  # 覆盖输出文件
                str(output_path),
            ]

            logger.info("开始优化视频格式为B站兼容格式")

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and output_path.exists():
                logger.info(f"视频优化完成: {output_path}")
                return output_path
            else:
                logger.error(f"视频优化失败: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"视频优化异常: {str(e)}")
            return None

    async def extract_thumbnail(
        self, video_path: Path, time_offset: str = "00:00:10"
    ) -> Optional[Path]:
        """提取视频缩略图"""
        try:
            thumbnail_path = self.temp_dir / f"thumbnail_{video_path.stem}.jpg"

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                time_offset,
                "-vframes",
                "1",
                "-q:v",
                "2",  # 高质量
                "-y",  # 覆盖输出文件
                str(thumbnail_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and thumbnail_path.exists():
                logger.info(f"缩略图提取成功: {thumbnail_path}")
                return thumbnail_path
            else:
                logger.error(f"缩略图提取失败: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"缩略图提取异常: {str(e)}")
            return None

    async def get_video_duration(self, video_path: Path) -> Optional[float]:
        """获取视频时长（秒）"""
        try:
            video_info = await self.get_video_info(video_path)
            if video_info:
                return float(video_info["format"].get("duration", 0))
            return None
        except Exception:
            return None

    async def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            logger.info("临时文件清理完成")
        except Exception as e:
            logger.error(f"清理临时文件失败: {str(e)}")
