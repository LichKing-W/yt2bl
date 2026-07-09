#!/usr/bin/env python3
"""Subscription监控脚本

检查subscription进程是否运行超过指定时长，如果超时则终止进程并清理锁文件。

用途：防止subscription进程在嵌入字幕等耗时操作中卡住，阻塞后续运行。

建议配置crontab每10-15分钟运行一次：
*/10 * * * * cd /path/to/yt2bl && python scripts/monitor_subscription.py
"""

import os
import sys
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
UPDATING_FILE = PROJECT_ROOT / ".updating"

# 默认超时时间（小时）
DEFAULT_TIMEOUT_HOURS = 6


def parse_updating_file(filepath: Path) -> Optional[tuple[int, datetime]]:
    """解析.updating文件，返回(PID, 启动时间)"""
    if not filepath.exists():
        return None

    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        pid = None
        start_time = None

        for line in lines:
            if line.startswith("PID:"):
                pid = int(line.split(":")[1].strip())
            elif line.startswith("Started:"):
                start_time = datetime.fromisoformat(line.split(":", 1)[1].strip())

        if pid and start_time:
            return pid, start_time

    except Exception as e:
        print(f"⚠️  解析.updating文件失败: {e}")

    return None


def is_process_running(pid: int) -> bool:
    """检查进程是否仍在运行"""
    try:
        # 发送信号0（不实际发送信号，只是检查进程是否存在）
        os.kill(pid, 0)
        return True
    except OSError:
        # 进程不存在或无权限访问
        return False


def terminate_process(pid: int, timeout: int = 30) -> bool:
    """终止进程

    先尝试SIGTERM，等待timeout秒后如果进程仍在运行则发送SIGKILL

    Returns:
        是否成功终止进程
    """
    import time

    try:
        # 先尝试SIGTERM（优雅终止）
        os.kill(pid, signal.SIGTERM)
        print(f"📤 发送SIGTERM信号到进程 {pid}")

        # 等待进程结束
        start = time.time()
        while time.time() - start < timeout:
            if not is_process_running(pid):
                print(f"✅ 进程 {pid} 已优雅终止")
                return True
            time.sleep(1)

        # 如果进程仍在运行，使用SIGKILL强制终止
        os.kill(pid, signal.SIGKILL)
        print(f"🔨 发送SIGKILL信号强制终止进程 {pid}")
        time.sleep(1)

        if not is_process_running(pid):
            print(f"✅ 进程 {pid} 已强制终止")
            return True
        else:
            print(f"⚠️  进程 {pid} 可能仍在运行")
            return False

    except ProcessLookupError:
        print(f"✅ 进程 {pid} 已不存在")
        return True
    except Exception as e:
        print(f"❌ 终止进程 {pid} 失败: {e}")
        return False


def cleanup_lock_file(filepath: Path) -> bool:
    """删除锁文件"""
    try:
        if filepath.exists():
            filepath.unlink()
            print(f"🗑️  已删除锁文件: {filepath}")
            return True
        else:
            print(f"ℹ️  锁文件不存在: {filepath}")
            return True
    except Exception as e:
        print(f"❌ 删除锁文件失败: {e}")
        return False


def check_and_kill(timeout_hours: int = DEFAULT_TIMEOUT_HOURS, dry_run: bool = False) -> bool:
    """检查并处理超时的subscription进程

    Args:
        timeout_hours: 超时时间（小时）
        dry_run: 仅检查不执行操作

    Returns:
        是否执行了清理操作
    """
    print(f"🔍 检查subscription进程状态...")
    print(f"📁 锁文件: {UPDATING_FILE}")
    print(f"⏰ 超时阈值: {timeout_hours} 小时")

    # 解析锁文件
    result = parse_updating_file(UPDATING_FILE)
    if not result:
        print("ℹ️  未检测到运行中的subscription进程")
        return False

    pid, start_time = result
    print(f"📋 进程信息:")
    print(f"   PID: {pid}")
    print(f"   启动时间: {start_time}")

    # 检查进程是否仍在运行
    if not is_process_running(pid):
        print(f"ℹ️  进程 {pid} 已结束，清理锁文件")
        if not dry_run:
            cleanup_lock_file(UPDATING_FILE)
        else:
            print("   [DRY RUN] 将删除锁文件")
        return True

    # 计算运行时长
    now = datetime.now()
    elapsed = now - start_time
    elapsed_hours = elapsed.total_seconds() / 3600

    print(f"⏱️  运行时长: {elapsed_hours:.2f} 小时")

    # 判断是否超时
    if elapsed_hours >= timeout_hours:
        print(f"⚠️  进程运行超过 {timeout_hours} 小时，需要终止")

        if dry_run:
            print("   [DRY RUN] 将执行以下操作:")
            print(f"     1. 终止进程 {pid}")
            print(f"     2. 删除锁文件 {UPDATING_FILE}")
            return True

        # 终止进程
        if terminate_process(pid):
            # 清理锁文件
            cleanup_lock_file(UPDATING_FILE)
            print("✅ 清理完成")
            return True
        else:
            print("❌ 终止进程失败")
            return False
    else:
        remaining = timeout_hours - elapsed_hours
        print(f"✅ 进程运行正常，剩余 {remaining:.2f} 小时到达超时")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="监控subscription进程，防止长时间运行阻塞",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查并终止超过6小时的进程
  python scripts/monitor_subscription.py

  # 自定义超时时间为3小时
  python scripts/monitor_subscription.py --timeout 3

  # 仅检查不执行操作
  python scripts/monitor_subscription.py --dry-run

推荐crontab配置（每10分钟检查一次）:
  */10 * * * * cd /path/to/yt2bl && python scripts/monitor_subscription.py >> logs/monitor.log 2>&1
        """
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_HOURS,
        help=f"超时时间（小时），默认 {DEFAULT_TIMEOUT_HOURS}",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅检查不执行操作",
    )

    args = parser.parse_args()

    # 执行检查
    acted = check_and_kill(timeout_hours=args.timeout, dry_run=args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN 模式 - 未实际执行任何操作]")

    # 返回码：0表示未执行操作，1表示执行了清理
    sys.exit(0 if not acted else 1)


if __name__ == "__main__":
    main()
