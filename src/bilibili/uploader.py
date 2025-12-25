"""Bilibili视频上传模块"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..utils.logger import logger
from ..utils.config import settings
from .models import BilibiliVideo, BilibiliUploadResult


class BilibiliUploader:
    """B站视频上传器"""

    def __init__(self) -> None:
        self.bili = None
        self.user_info = None
        self._initialized = False

    async def _ensure_initialized(self) -> bool:
        """确保已初始化Bilibili客户端"""
        if self._initialized:
            return True

        try:
            from bilibili_api import Credential, sync
            import aiohttp

            # 检查认证信息
            if not all([
                settings.bilibili_sessdata,
                settings.bilibili_bili_jct,
                settings.bilibili_dedeuser_id,
            ]):
                logger.error("缺少Bilibili认证信息，请在.env文件中配置")
                return False

            # 创建认证对象
            self.credential = Credential(
                sessdata=settings.bilibili_sessdata,
                bili_jct=settings.bilibili_bili_jct,
                dedeuserid=settings.bilibili_dedeuser_id,
            )

            # 导入视频上传模块
            from bilibili_api import video_uploader

            self.video_uploader = video_uploader
            self._initialized = True
            logger.info("Bilibili客户端初始化成功")
            return True

        except ImportError as e:
            logger.error(f"缺少bilibili-api-python库: {str(e)}")
            logger.error("请运行: pip install bilibili-api-python")
            return False
        except Exception as e:
            logger.error(f"Bilibili客户端初始化失败: {str(e)}")
            return False

    async def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            if not await self._ensure_initialized():
                return False

            from bilibili_api import user

            # 获取用户信息
            me = user.User(int(self.credential.dedeuserid), credential=self.credential)
            info = await me.get_user_info()

            if info:
                self.user_info = info
                logger.info(f"登录成功，用户: {info.get('name', 'Unknown')}")
                return True
            else:
                logger.error("获取用户信息失败")
                return False

        except Exception as e:
            logger.error(f"检查登录状态失败: {str(e)}")
            return False

    async def upload_video(self, video: BilibiliVideo) -> BilibiliUploadResult:
        """上传视频到B站"""
        start_time = time.time()

        try:
            logger.info(f"开始上传视频: {video.title}")

            # 检查登录状态
            if not await self.check_login_status():
                return BilibiliUploadResult(success=False, message="登录状态验证失败")

            # 检查视频文件
            video_path = Path(video.video_path)
            if not video_path.exists():
                return BilibiliUploadResult(
                    success=False, message=f"视频文件不存在: {video.video_path}"
                )

            # 获取文件大小
            file_size = video_path.stat().st_size
            logger.info(f"视频文件大小: {file_size / (1024 * 1024):.1f}MB")

            # 检查文件大小限制
            max_size = settings.max_video_size_mb * 1024 * 1024
            if file_size > max_size:
                return BilibiliUploadResult(
                    success=False,
                    message=f"视频文件过大: {file_size / (1024 * 1024):.1f}MB (最大{settings.max_video_size_mb}MB)"
                )

            # 上传视频
            result = await self._upload_video_internal(video, video_path)

            upload_duration = time.time() - start_time

            if result:
                return BilibiliUploadResult(
                    success=True,
                    bvid=result.get("bvid"),
                    aid=result.get("aid"),
                    message="视频上传成功",
                    file_size=file_size,
                    upload_duration=upload_duration,
                )
            else:
                return BilibiliUploadResult(
                    success=False,
                    message="视频上传失败",
                    file_size=file_size,
                    upload_duration=upload_duration,
                )

        except Exception as e:
            import traceback
            upload_duration = time.time() - start_time
            logger.error(f"视频上传异常: {str(e)}\n{traceback.format_exc()}")
            return BilibiliUploadResult(
                success=False,
                message=f"上传异常: {str(e)}",
                upload_duration=upload_duration,
            )

    async def _upload_video_internal(
        self, video: BilibiliVideo, video_path: Path
    ) -> Optional[Dict[str, Any]]:
        """内部上传实现"""
        try:
            # 准备视频封面
            from bilibili_api.utils.picture import Picture

            # 如果没有提供封面，创建一个简单的临时封面
            if video.cover_path and Path(video.cover_path).exists():
                cover = Picture().from_file(Path(video.cover_path))
            else:
                # 创建一个临时封面图片（1x1像素的PNG）
                import tempfile
                import os

                # 创建一个最小的PNG文件（1x1像素透明PNG）
                minimal_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

                # 保存到临时文件
                temp_cover = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_cover.write(minimal_png)
                temp_cover.close()

                cover = Picture().from_file(str(temp_cover.name))
                logger.info("使用临时封面图片")

            # 准备视频页面信息（使用VideoUploaderPage类）
            from bilibili_api.video_uploader import VideoUploaderPage

            page = VideoUploaderPage(
                path=str(video_path),
                title=video.title,
                description=video.description[:200] if video.description else "",  # 前200字作为简介
            )

            # 准备元数据
            meta = {
                "title": video.title,
                "tid": video.tid,
                "tag": ",".join(video.tags[:12]),  # B站限制12个标签
                "desc": video.description,
                "cover": cover,  # 使用Picture对象
                "source": video.source or "",
                "dynamic": video.dynamic or "",
                "copyright": video.copyright,
                "repost_desc": video.repost_desc or "",
            }

            # 创建上传器实例，显式传递cover参数
            uploader = self.video_uploader.VideoUploader(
                pages=[page],
                meta=meta,
                credential=self.credential,
                cover=cover,  # 显式传递cover，使用我们创建的Picture对象
            )

            # 进度回调
            def on_progress(event):
                # bilibili_api的回调函数接收event对象
                if hasattr(event, 'data'):
                    progress = event.data
                else:
                    progress = 0
                logger.info(f"上传进度: {progress:.1f}%")

            uploader.on("progress")(on_progress)

            # 执行上传
            logger.info("开始上传到B站...")
            result = await uploader.start()

            if result:
                logger.info(f"上传成功: {result}")
                return {"bvid": result.get("bvid"), "aid": result.get("aid")}
            else:
                logger.error("上传失败")
                return None

        except Exception as e:
            logger.error(f"上传过程失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def _upload_cover(self, cover_path: Path) -> Optional[str]:
        """上传封面图片"""
        try:
            from bilibili_api import video_uploader

            logger.info(f"上传封面: {cover_path.name}")

            # 使用bilibili-api上传封面
            cover_url = await video_uploader.upload_cover(
                str(cover_path),
                credential=self.credential
            )

            if cover_url:
                logger.info(f"封面上传成功: {cover_url}")
                return cover_url
            else:
                logger.warning("封面上传失败，将使用默认封面")
                return None

        except Exception as e:
            logger.warning(f"封面上传异常: {str(e)}，将使用默认封面")
            return None

    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取当前用户信息"""
        try:
            if not await self._ensure_initialized():
                return None

            from bilibili_api import user

            me = user.User(int(self.credential.dedeuserid), credential=self.credential)
            info = await me.get_user_info()

            return info

        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return None

    async def get_video_status(self, bvid: str) -> Optional[Dict[str, Any]]:
        """获取视频状态"""
        try:
            if not await self._ensure_initialized():
                return None

            from bilibili_api import video

            v = video.Video(bvid=bvid, credential=self.credential)
            info = await v.get_info()

            return info

        except Exception as e:
            logger.error(f"获取视频状态失败: {str(e)}")
            return None

    async def batch_upload(
        self, videos: List[BilibiliVideo], delay: int = 60
    ) -> List[BilibiliUploadResult]:
        """批量上传视频"""
        results = []

        for i, video in enumerate(videos):
            logger.info(f"正在上传第 {i+1}/{len(videos)} 个视频")

            result = await self.upload_video(video)
            results.append(result)

            # 如果不是最后一个视频，等待一段时间
            if i < len(videos) - 1:
                logger.info(f"等待 {delay} 秒后继续下一个视频...")
                await asyncio.sleep(delay)

        return results
