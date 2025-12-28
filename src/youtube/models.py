"""YouTube数据模型"""

from datetime import datetime
from typing import List, Optional
import re


class YouTubeVideo:
    """YouTube视频信息模型"""

    def __init__(self, **kwargs):
        # 设置默认值
        self.video_id: str = kwargs.get("video_id", "")
        self.title: str = kwargs.get("title", "")
        self.description: str = kwargs.get("description", "")
        self.channel_title: str = kwargs.get("channel_title", "")
        self.channel_id: str = kwargs.get("channel_id", "")
        self.published_at: datetime = kwargs.get("published_at", datetime.now())
        self.duration: Optional[str] = kwargs.get("duration")
        self.view_count: int = kwargs.get("view_count", 0)
        self.like_count: int = kwargs.get("like_count", 0)
        self.comment_count: int = kwargs.get("comment_count", 0)
        self.thumbnail_url: Optional[str] = kwargs.get("thumbnail_url")
        self.tags: List[str] = kwargs.get("tags", [])
        self.language: Optional[str] = kwargs.get("language")
        self.category_id: Optional[str] = kwargs.get("category_id")

        # 额外属性
        self.downloaded_path: Optional[str] = kwargs.get("downloaded_path")

    @property
    def url(self) -> str:
        """获取视频URL"""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def short_url(self) -> str:
        """获取短URL"""
        return f"https://youtu.be/{self.video_id}"

    @property
    def folder_name(self) -> str:
        """获取视频文件夹名称 (格式: {作者名}_{视频ID})"""
        # 清理作者名中的非法字符
        safe_author = self._sanitize_for_folder(self.channel_title)
        return f"{safe_author}_{self.video_id}"

    def _sanitize_for_folder(self, name: str) -> str:
        """清理文件夹名称，移除非法字符"""
        # 移除或替换非法字符（文件夹名中不能有 / \\ : * ? " < > |）
        illegal_chars = '/\\:*?"<>|'
        for char in illegal_chars:
            name = name.replace(char, "_")

        # 限制长度
        if len(name) > 50:
            name = name[:50]

        # 移除首尾空格和点
        name = name.strip(". ")

        return name or "Unknown"

    def is_computer_science_related(self) -> bool:
        """判断是否与计算机科学相关"""
        cs_keywords = [
            "programming",
            "coding",
            "software",
            "development",
            "python",
            "javascript",
            "java",
            "c++",
            "algorithm",
            "data structure",
            "machine learning",
            "ai",
            "artificial intelligence",
            "web development",
            "frontend",
            "backend",
            "database",
            "devops",
            "docker",
            "kubernetes",
            "cloud",
            "aws",
            "azure",
            "google cloud",
            "cybersecurity",
            "hacking",
            "blockchain",
            "cryptocurrency",
            "game development",
            "mobile app",
            "ios",
            "android",
            "react",
            "vue",
            "angular",
            "node.js",
            "django",
            "flask",
            "tensorflow",
            "pytorch",
            "data science",
            "analytics",
            "big data",
        ]

        # 检查标题、描述和标签中的关键词
        text_to_check = (
            self.title.lower()
            + " "
            + self.description.lower()
            + " "
            + " ".join(self.tags).lower()
        )

        return any(keyword in text_to_check for keyword in cs_keywords)

    def get_quality_score(self) -> float:
        """计算视频质量评分"""
        if self.view_count == 0:
            return 0.0

        # 基础分数：观看量
        base_score = min(self.view_count / 10000, 10.0)

        # 互动率加分
        if self.view_count > 0:
            engagement_rate = (self.like_count + self.comment_count) / self.view_count
            engagement_bonus = min(engagement_rate * 100, 5.0)
        else:
            engagement_bonus = 0.0

        # 时长加分（10-30分钟最佳）
        duration_bonus = 0.0
        if self.duration:
            minutes = self._parse_duration_minutes()
            if 10 <= minutes <= 30:
                duration_bonus = 2.0
            elif 5 <= minutes <= 60:
                duration_bonus = 1.0

        return min(base_score + engagement_bonus + duration_bonus, 10.0)

    def _parse_duration_minutes(self) -> int:
        """解析时长为分钟数"""
        if not self.duration:
            return 0

        # 解析ISO 8601格式 (PT10M30S)
        match = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", self.duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 60 + minutes + (1 if seconds > 30 else 0)

        return 0


class YouTubeChannel:
    """YouTube频道信息模型"""

    def __init__(self, **kwargs):
        self.channel_id: str = kwargs.get("channel_id", "")
        self.title: str = kwargs.get("title", "")
        self.description: str = kwargs.get("description", "")
        self.subscriber_count: int = kwargs.get("subscriber_count", 0)
        self.video_count: int = kwargs.get("video_count", 0)
        self.view_count: int = kwargs.get("view_count", 0)
        self.thumbnail_url: Optional[str] = kwargs.get("thumbnail_url")
        self.country: Optional[str] = kwargs.get("country")
        self.language: Optional[str] = kwargs.get("language")

    @property
    def url(self) -> str:
        """获取频道URL"""
        return f"https://www.youtube.com/channel/{self.channel_id}"
