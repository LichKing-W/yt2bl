"""视频处理器测试"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.core.video_processor import VideoProcessor


@pytest.fixture
def processor():
    """创建视频处理器实例"""
    return VideoProcessor()


@pytest.fixture
def mock_video_path():
    """模拟视频文件路径"""
    return Path("/tmp/test_video.mp4")


class TestVideoProcessor:
    """视频处理器测试类"""
    
    @pytest.mark.asyncio
    async def test_get_video_info(self, processor):
        """测试获取视频信息"""
        mock_info = {
            'format': {
                'duration': '120.5',
                'size': '10485760'
            },
            'streams': [
                {
                    'codec_type': 'video',
                    'width': 1920,
                    'height': 1080
                }
            ]
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b'{"format": {"duration": "120.5"}, "streams": []}',
                b''
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            info = await processor.get_video_info(Path("test.mp4"))
            assert info is not None
            assert 'format' in info
    
    @pytest.mark.asyncio
    async def test_get_video_duration(self, processor):
        """测试获取视频时长"""
        with patch.object(processor, 'get_video_info') as mock_get_info:
            mock_get_info.return_value = {
                'format': {'duration': '120.5'}
            }
            
            duration = await processor.get_video_duration(Path("test.mp4"))
            assert duration == 120.5
            assert isinstance(duration, float)
    
    def test_init(self, processor):
        """测试初始化"""
        assert processor.temp_dir.exists()
        assert processor.temp_dir.name == "youtube_to_bilibili"
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, processor):
        """测试清理临时文件"""
        # 创建一些临时文件
        test_file = processor.temp_dir / "test.txt"
        test_file.write_text("test")
        
        # 确保文件存在
        assert test_file.exists()
        
        # 清理文件
        await processor.cleanup_temp_files()
        
        # 文件应该被删除
        assert not test_file.exists()


class TestVideoProcessorIntegration:
    """视频处理器集成测试"""
    
    @pytest.mark.asyncio
    async def test_process_video_file_not_exists(self, processor):
        """测试处理不存在的视频文件"""
        non_existent_path = Path("/tmp/non_existent_video.mp4")
        
        result = await processor.process_video(non_existent_path)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_compress_video(self, processor):
        """测试视频压缩（模拟）"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'', b'')
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB
                    
                    result = await processor.compress_video(Path("test.mp4"))
                    assert result is not None
