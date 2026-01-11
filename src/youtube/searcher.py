"""YouTube视频搜索模块"""

import asyncio
import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ..utils.logger import logger
from ..utils.config import settings
from .models import YouTubeVideo, YouTubeChannel


class YouTubeSearcher:
    """YouTube视频搜索器"""

    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com"
        self.api_key = settings.youtube_api_key

        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
        else:
            self.session = None
            logger.warning("requests模块不可用，搜索功能受限")

    async def search_trending_cs_videos(
        self, max_results: int = 20
    ) -> List[YouTubeVideo]:
        """搜索计算机领域热门视频"""
        if self.api_key and REQUESTS_AVAILABLE:
            return await self._search_with_api(max_results)
        else:
            return await self._search_with_scraping(max_results)

    async def _search_with_api(self, max_results: int) -> List[YouTubeVideo]:
        """使用YouTube API搜索"""
        try:
            # 计算机科学相关关键词
            keywords = [
                "programming tutorial",
                "python programming",
                "javascript tutorial",
                "web development",
                "machine learning",
                "data science",
                "software engineering",
                "coding interview",
            ]

            all_videos = []

            for keyword in keywords[:3]:  # 限制关键词数量
                videos = await self._api_search_by_keyword(keyword, max_results // 3)
                all_videos.extend(videos)

            # 去重并按质量评分排序
            unique_videos = self._deduplicate_videos(all_videos)
            sorted_videos = sorted(
                unique_videos, key=lambda v: v.get_quality_score(), reverse=True
            )

            return sorted_videos[:max_results]

        except Exception as e:
            logger.error(f"API搜索失败: {str(e)}")
            return await self._search_without_api(max_results)

    async def _api_search_by_keyword(
        self, keyword: str, max_results: int
    ) -> List[YouTubeVideo]:
        """通过关键词搜索"""
        try:
            # 搜索视频
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "relevance",
                "maxResults": min(max_results, 50),
                "publishedAfter": (datetime.now() - timedelta(days=30)).isoformat()
                + "Z",
                "key": self.api_key,
            }

            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

            video_ids = [item["id"]["videoId"] for item in data.get("items", [])]

            if not video_ids:
                return []

            # 获取详细信息
            return await self._get_video_details(video_ids)

        except Exception as e:
            logger.error(f"关键词搜索失败 {keyword}: {str(e)}")
            return []

    async def _get_video_details(self, video_ids: List[str]) -> List[YouTubeVideo]:
        """获取视频详细信息"""
        try:
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": self.api_key,
            }

            response = self.session.get(videos_url, params=params)
            response.raise_for_status()
            data = response.json()

            videos = []
            for item in data.get("items", []):
                try:
                    video = self._parse_video_item(item)
                    if video and video.is_computer_science_related():
                        videos.append(video)
                except Exception as e:
                    logger.error(f"解析视频失败: {str(e)}")
                    continue

            return videos

        except Exception as e:
            logger.error(f"获取视频详情失败: {str(e)}")
            return []

    def _parse_video_item(self, item: Dict[str, Any]) -> Optional[YouTubeVideo]:
        """解析API返回的视频数据"""
        try:
            snippet = item["snippet"]
            statistics = item.get("statistics", {})
            content_details = item.get("contentDetails", {})

            return YouTubeVideo(
                video_id=item["id"],
                title=snippet["title"],
                description=snippet["description"],
                channel_title=snippet["channelTitle"],
                channel_id=snippet["channelId"],
                published_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
                duration=content_details.get("duration"),
                view_count=int(statistics.get("viewCount", 0)),
                like_count=int(statistics.get("likeCount", 0)),
                comment_count=int(statistics.get("commentCount", 0)),
                thumbnail_url=snippet["thumbnails"].get("high", {}).get("url"),
                tags=snippet.get("tags", []),
                language=snippet.get("defaultLanguage", "en"),
                category_id=snippet.get("categoryId"),
            )

        except Exception as e:
            logger.error(f"解析视频数据失败: {str(e)}")
            return None

    async def _search_with_scraping(self, max_results: int) -> List[YouTubeVideo]:
        """使用已知的教育视频ID进行搜索"""
        try:
            logger.info("使用已知教育视频ID进行搜索")

            # 使用一些知名的编程教育视频ID
            educational_video_ids = [
                "rfscVS0vtbw",  # Learn Python - Full Course for Beginners
                "8ext9G7xspg",  # Python Tutorial for Beginners
                "t8pPdKYpowI",  # HTML Crash Course
                "UB1O30fR-EE",  # HTML CSS JavaScript
                "PkZNo7MFNFg",  # Learn JavaScript
                "W6NZfCO5SIk",  # JavaScript Tutorial
                "Tn6-PIqc4UM",  # React in 100 Seconds
                "SqcY0GlETPk",  # React Tutorial for Beginners
            ]

            videos = []

            for video_id in educational_video_ids[:max_results]:
                try:
                    video_info = await self._get_video_info_from_id(video_id)
                    if video_info:
                        videos.append(video_info)
                except Exception as e:
                    logger.debug(f"获取视频信息失败 {video_id}: {str(e)}")
                    continue

            return videos

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    async def _get_video_info_from_id(self, video_id: str) -> Optional[YouTubeVideo]:
        """从视频ID获取视频信息"""
        try:
            # 使用yt-dlp获取视频信息
            try:
                import yt_dlp

                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                }

                # 如果配置了代理，添加代理支持
                if settings.proxy:
                    ydl_opts["proxy"] = settings.proxy

                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(
                    None,
                    self._extract_info_sync,
                    f"https://www.youtube.com/watch?v={video_id}",
                    ydl_opts,
                )

                if info:
                    return self._parse_video_info_from_ytdlp(info)

            except ImportError:
                logger.error("yt-dlp不可用")
                return None

        except Exception as e:
            logger.debug(f"获取视频信息失败: {str(e)}")
            return None

    def _extract_info_sync(self, url: str, ydl_opts: dict) -> Optional[Dict[str, Any]]:
        """同步提取视频信息"""
        try:
            import yt_dlp

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.debug(f"提取信息失败: {str(e)}")
            return None

    def _parse_video_info_from_ytdlp(
        self, info: Dict[str, Any]
    ) -> Optional[YouTubeVideo]:
        """从yt-dlp信息解析视频数据"""
        try:
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
                category_id=str(info.get("categories", [""])[0])
                if info.get("categories")
                else None,
            )

        except Exception as e:
            logger.error(f"解析视频信息失败: {str(e)}")
            return None

    def _deduplicate_videos(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """去除重复视频"""
        seen_ids = set()
        unique_videos = []

        for video in videos:
            if video.video_id not in seen_ids:
                seen_ids.add(video.video_id)
                unique_videos.append(video)

        return unique_videos

    async def get_video_info(self, video_url: str) -> Optional[YouTubeVideo]:
        """获取单个视频信息"""
        video_id = self._extract_video_id(video_url)
        if not video_id:
            return None

        if self.api_key and REQUESTS_AVAILABLE:
            videos = await self._get_video_details([video_id])
            return videos[0] if videos else None
        else:
            # 返回模拟数据
            return YouTubeVideo(
                video_id=video_id,
                title=f"视频 {video_id}",
                description="这是一个模拟的视频描述。",
                channel_title="模拟频道",
                channel_id="mock_channel",
                published_at=datetime.now(),
                duration="PT10M30S",
                view_count=1000,
                like_count=100,
                comment_count=10,
                thumbnail_url=f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                tags=["mock", "video"],
                language="en",
                category_id="28",
            )

    def _extract_video_id(self, url: str) -> Optional[str]:
        """从URL提取视频ID"""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    async def search_by_channel(
        self,
        channel_id: str,
        max_results: int = 20,
        order: str = "date"
    ) -> List[YouTubeVideo]:
        """根据频道ID获取视频列表

        Args:
            channel_id: YouTube频道ID (如 UCq6XkhO5SZ66N0xJ0WyIcyw) 或频道handle (如 @TsodingDaily)
            max_results: 最大返回视频数量
            order: 排序方式 (date, viewCount, rating)

        Returns:
            视频列表
        """
        # 规范化频道标识符（支持 @username 格式）
        channel_identifier = self._normalize_channel_identifier(channel_id)

        if self.api_key and REQUESTS_AVAILABLE:
            # 如果是handle格式，先转换为频道ID
            actual_channel_id = await self._resolve_channel_id(channel_identifier)
            if not actual_channel_id:
                # 降级到yt-dlp
                return await self._search_channel_by_ytdlp(channel_identifier, max_results)
            return await self._search_channel_by_api(actual_channel_id, max_results, order)
        else:
            return await self._search_channel_by_ytdlp(channel_identifier, max_results)

    def _normalize_channel_identifier(self, channel_id: str) -> str:
        """规范化频道标识符
        支持:
        - UCxxxxxxxxxxxxxxxxxx (频道ID)
        - @username (频道handle)
        - https://www.youtube.com/@username
        - https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxx
        - https://www.youtube.com/c/username
        """
        # 如果是完整URL，提取频道部分
        if channel_id.startswith("http"):
            # 匹配各种YouTube频道URL格式
            patterns = [
                r"/@([\w-]+)",  # @username
                r"/channel/(UC[\w-]+)",  # /channel/UC...
                r"/c/([\w-]+)",  # /c/username
                r"/user/([\w-]+)",  # /user/username
            ]
            for pattern in patterns:
                match = re.search(pattern, channel_id)
                if match:
                    identifier = match.group(1)
                    # 如果不是以UC开头的频道ID，添加@前缀
                    if not identifier.startswith("UC"):
                        return f"@{identifier}"
                    return identifier
            return channel_id

        # 如果已经是@username格式，直接返回
        if channel_id.startswith("@"):
            return channel_id

        # 如果是UC开头的频道ID，直接返回
        if channel_id.startswith("UC"):
            return channel_id

        # 否则当作username处理，添加@前缀
        return f"@{channel_id}"

    async def _resolve_channel_id(self, channel_identifier: str) -> Optional[str]:
        """将频道handle或用户名转换为频道ID"""
        try:
            # 如果已经是频道ID，直接返回
            if channel_identifier.startswith("UC"):
                return channel_identifier

            # 构建频道URL
            if channel_identifier.startswith("@"):
                channel_url = f"https://www.youtube.com/{channel_identifier}"
            else:
                channel_url = f"https://www.youtube.com/c/{channel_identifier}"

            # 使用yt-dlp获取频道信息
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }

            # 如果配置了代理，添加代理支持
            if settings.proxy:
                ydl_opts["proxy"] = settings.proxy

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                self._extract_info_sync,
                channel_url,
                ydl_opts,
            )

            if info:
                return info.get("channel_id")

            return None

        except Exception as e:
            logger.debug(f"解析频道ID失败: {str(e)}")
            return None

    async def _search_channel_by_api(
        self,
        channel_id: str,
        max_results: int,
        order: str
    ) -> List[YouTubeVideo]:
        """使用YouTube API获取频道视频"""
        try:
            # 获取频道的上传列表ID
            channel_url = "https://www.googleapis.com/youtube/v3/channels"
            params = {
                "part": "contentDetails",
                "id": channel_id,
                "key": self.api_key,
            }

            response = self.session.get(channel_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("items"):
                logger.error(f"未找到频道: {channel_id}")
                return []

            uploads_playlist_id = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # 获取上传列表中的视频
            playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
            params = {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": min(max_results, 50),
                "order": order,
                "key": self.api_key,
            }

            response = self.session.get(playlist_url, params=params)
            response.raise_for_status()
            data = response.json()

            video_ids = [item["contentDetails"]["videoId"] for item in data.get("items", [])]

            if not video_ids:
                return []

            # 获取视频详细信息
            return await self._get_video_details(video_ids)

        except Exception as e:
            logger.error(f"API获取频道视频失败: {str(e)}")
            # 降级到yt-dlp
            return await self._search_channel_by_ytdlp(channel_id, max_results)

    async def _search_channel_by_ytdlp(
        self,
        channel_identifier: str,
        max_results: int
    ) -> List[YouTubeVideo]:
        """使用yt-dlp获取频道视频"""
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,  # 快速提取，不下载
                "playlistend": max_results,
            }

            # 如果配置了代理，添加代理支持
            if settings.proxy:
                ydl_opts["proxy"] = settings.proxy

            # 根据频道标识符格式构建URL（添加/videos后缀获取视频列表）
            if channel_identifier.startswith("@"):
                channel_url = f"https://www.youtube.com/{channel_identifier}/videos"
            elif channel_identifier.startswith("UC"):
                channel_url = f"https://www.youtube.com/channel/{channel_identifier}/videos"
            else:
                # 用户名格式
                channel_url = f"https://www.youtube.com/c/{channel_identifier}/videos"

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                self._extract_info_sync,
                channel_url,
                ydl_opts,
            )

            if not info or "entries" not in info:
                logger.error(f"无法获取频道视频: {channel_identifier}")
                return []

            # 从顶层info获取频道信息（因为entries中可能是None）
            channel_title = info.get("uploader") or info.get("channel") or channel_identifier
            channel_id = info.get("channel_id") or channel_identifier

            videos = []
            for entry in info["entries"][:max_results]:
                try:
                    video = YouTubeVideo(
                        video_id=entry.get("id", ""),
                        title=entry.get("title", ""),
                        description=entry.get("description", ""),
                        channel_title=entry.get("uploader") or entry.get("channel") or channel_title,
                        channel_id=entry.get("channel_id") or channel_id,
                        published_at=datetime.now(),
                        duration=None,  # extract_flat模式不包含时长
                        view_count=entry.get("view_count") or 0,
                        like_count=0,
                        comment_count=0,
                        thumbnail_url=entry.get("thumbnail"),
                        tags=[],
                        language="en",
                        category_id=None,
                    )
                    videos.append(video)
                except Exception as e:
                    logger.debug(f"解析视频失败: {str(e)}")
                    continue

            return videos

        except ImportError:
            logger.error("yt-dlp不可用")
            return []
        except Exception as e:
            import traceback
            logger.error(f"yt-dlp获取频道视频失败: {str(e)}\n{traceback.format_exc()}")
            return []
