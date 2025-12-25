#!/bin/bash
# 开发环境运行脚本
echo "🚀 YouTube to Bilibili 开发环境启动"
echo "========================================="

# 设置Python路径
export PYTHONPATH="/home/keith/youtube-projects:$PYTHONPATH"

echo "✅ 环境变量已设置"
echo "✅ Python路径: $PYTHONPATH"

# 检查目录结构
echo "\n📁 检查目录结构:"
ls -la src/ test/ data/ logs/ 2>/dev/null || echo "目录已存在"

# 运行主程序
echo "\n🎬 启动主程序..."
python -c "
import sys
sys.path.insert(0, '/home/keith/youtube-projects')
from src.main import cli
cli()
"
