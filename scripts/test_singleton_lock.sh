#!/bin/bash
# 测试订阅监控器的单例锁功能

echo "========================================"
echo "测试订阅监控器单例锁"
echo "========================================"
echo ""

# 清理旧文件
rm -f .updating

echo "1. 测试正常启动（无.updating文件）"
echo "-----------------------------------"
timeout 3 python -m src.subscription_monitor --help > /dev/null 2>&1
if [ -f .updating ]; then
    echo "✅ .updating文件已创建"
    cat .updating
    rm -f .updating
else
    echo "❌ .updating文件未创建"
fi
echo ""

echo "2. 测试检测已有实例（有.updating文件）"
echo "-----------------------------------"
echo "PID: 99999" > .updating
echo "Started: $(date -Iseconds)" >> .updating
echo "创建假的.updating文件："
cat .updating
echo ""
echo "尝试启动新实例："
python -m src.subscription_monitor --help 2>&1 | grep -E "(检测到|取消|⚠)" || true
echo ""
rm -f .updating
echo "✅ 测试完成，清理.updating文件"
echo ""

echo "3. 测试异常退出后清理"
echo "-----------------------------------"
# 模拟异常情况
echo "测试异常情况下的清理..."

# 启动一个会快速失败的进程
python -c "
import asyncio
from pathlib import Path
from datetime import datetime

# 创建.updating文件
updating_file = Path('.updating')
updating_file.write_text(f'PID: {__import__(\"os\").getpid()}\nStarted: {datetime.now().isoformat()}\n')
print('创建.updating文件')

# 模拟异常
raise Exception('测试异常')
" 2>/dev/null

if [ -f .updating ]; then
    echo "❌ 异常后.updating文件未清理（这是预期行为，需要手动清理）"
    rm -f .updating
else
    echo "⚠️  .updating文件已被Python异常清理"
fi
echo ""

echo "========================================"
echo "单例锁测试完成"
echo "========================================"
