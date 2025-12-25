#!/bin/bash
# 快速测试项目功能
echo "🎯 YouTube to Bilibili 项目测试"
echo "================================="

echo "📍 当前目录: $(pwd)"
echo "📁 项目结构:"
find . -name '*.py' | head -10

echo "\n🔧 测试核心模块..."

# 测试配置模块
export PYTHONPATH="/home/keith/youtube-projects:$PYTHONPATH"

python -c "
import sys
sys.path.insert(0, '/home/keith/youtube-projects')
print('\n✅ 配置模块测试:')
from src.utils.config import settings
print(f'   下载路径: {settings.download_path}')
print(f'   日志级别: {settings.log_level}')
" | head -5

python -c "
import sys
sys.path.insert(0, '/home/keith/youtube-projects')
print('\n✅ 视频模型测试:')
from src.youtube.models import YouTubeVideo
from datetime import datetime
v = YouTubeVideo(video_id='test', title='Python Tutorial', description='', channel_title='', channel_id='', published_at=datetime.now())
print(f'   CS相关: {v.is_computer_science_related()}')
print(f'   质量评分: {v.get_quality_score():.1f}')
" | head -5

python -c "
import sys
sys.path.insert(0, '/home/keith/youtube-projects')
print('\n✅ 最小版本主程序测试:')
from src.main_minimal import YouTubeToBilibiliMinimal
print('   主程序类导入成功')
" | head -3

echo "\n🎊 基础功能测试完成！"
echo "\n📝 使用说明:"
echo "   - 运行最小版本: ./scripts/test_minimal.sh"
echo "   - 开发环境运行: ./scripts/run_dev.sh"
echo "   - 查看安装指南: cat INSTALL_GUIDE.md"
