#!/bin/bash
# 测试最小版本
echo "🧪 测试最小版本功能"
echo "========================="

# 设置环境变量
export PYTHONPATH="/home/keith/youtube-projects:$PYTHONPATH"

# 运行最小版本
python -c "
import sys
sys.path.insert(0, '/home/keith/youtube-projects')
from src.main_minimal import YouTubeToBilibiliMinimal
import asyncio

async def test():
    app = YouTubeToBilibiliMinimal()
    await app.run(3)

asyncio.run(test())
"
