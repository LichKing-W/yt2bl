#!/bin/bash
# Subscription监控脚本包装器
# 用于检测并终止运行过长的subscription进程

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

# 运行监控脚本（默认6小时超时）
python scripts/monitor_subscription.py "$@" >> logs/monitor.log 2>&1
