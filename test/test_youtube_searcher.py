"""YouTube搜索器测试"""
import pytest
import asyncio
from unittest.mock import Mock, patch

from src.youtube.searcher import YouTubeSearcher
from src.youtube.models import YouTubeVideo


@pytest.fixture
def searcher():
    """创建搜索器实例"""
    return YouTubeSearcher()


@pytest.fixture
def sample_video():
    """示例视频数据"""
    return YouTubeVideo(
        video_id="test123",
        title="Python Programming Tutorial for Beginners",
        description="Learn Python programming from scratch",
        channel_title="Tech Channel",
        channel_id="channel123",
        published_at="2024-01-01T00:00:00",
        view_count=10000,
        like_count=500,
        comment_count=100,
        tags=["python", "programming", "tutorial"],
        language="en",
        category_id="28"
    )


class TestYouTubeSearcher:
    """YouTube搜索器测试类"""
    
    @pytest.mark.asyncio
    async def test_search_trending_cs_videos(self, searcher):
        """测试搜索CS热门视频"""
        # 这里需要mock网络请求
        with patch('requests.Session.get') as mock_get:
            # 模拟响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = """
            <html>
                <div id="contents">
                    <div id="dismissable1">
                        <a id="video-title" href="/watch?v=test123">Python Tutorial</a>
                        <a class="yt-simple-endpoint">Tech Channel</a>
                        <span>10K views</span>
                        <span>1 day ago</span>
                    </div>
                </div>
            </html>
            """
            mock_get.return_value = mock_response
            
            videos = await searcher.search_trending_cs_videos(max_results=5)
            
            assert len(videos) <= 5
            # 更多的断言...
    
    def test_parse_view_count(self, searcher):
        """测试观看次数解析"""
        assert searcher._parse_view_count("10K views") == 10000
        assert searcher._parse_view_count("1.5M views") == 1500000
        assert searcher._parse_view_count("500 views") == 500
        assert searcher._parse_view_count("invalid") == 0
    
    def test_parse_published_time(self, searcher):
        """测试发布时间解析"""
        from datetime import datetime, timedelta
        
        # 测试小时
        time_2h_ago = searcher._parse_published_time("2 hours ago")
        assert isinstance(time_2h_ago, datetime)
        
        # 测试天数
        time_3d_ago = searcher._parse_published_time("3 days ago")
        assert isinstance(time_3d_ago, datetime)
    
    def test_deduplicate_videos(self, searcher):
        """测试视频去重"""
        video1 = YouTubeVideo(
            video_id="test1",
            title="Video 1",
            description="",
            channel_title="",
            channel_id="",
            published_at="2024-01-01T00:00:00"
        )
        
        video2 = YouTubeVideo(
            video_id="test1",  # 相同ID
            title="Video 1 Duplicate",
            description="",
            channel_title="",
            channel_id="",
            published_at="2024-01-01T00:00:00"
        )
        
        video3 = YouTubeVideo(
            video_id="test2",
            title="Video 2",
            description="",
            channel_title="",
            channel_id="",
            published_at="2024-01-01T00:00:00"
        )
        
        unique_videos = searcher._deduplicate_videos([video1, video2, video3])
        assert len(unique_videos) == 2
        assert all(v.video_id in ["test1", "test2"] for v in unique_videos)


class TestYouTubeVideo:
    """YouTube视频模型测试类"""
    
    def test_is_computer_science_related(self, sample_video):
        """测试CS相关性判断"""
        # 测试包含CS关键词的视频
        assert sample_video.is_computer_science_related()
        
        # 测试不包含CS关键词的视频
        non_cs_video = YouTubeVideo(
            video_id="test456",
            title="Cooking Recipe",
            description="Learn how to cook",
            channel_title="Food Channel",
            channel_id="food123",
            published_at="2024-01-01T00:00:00"
        )
        assert not non_cs_video.is_computer_science_related()
    
    def test_quality_score(self, sample_video):
        """测试质量评分"""
        score = sample_video.get_quality_score()
        assert 0 <= score <= 100
        assert isinstance(score, float)
    
    def test_url_properties(self, sample_video):
        """测试URL属性"""
        assert sample_video.url == "https://www.youtube.com/watch?v=test123"
        assert sample_video.short_url == "https://youtu.be/test123"
