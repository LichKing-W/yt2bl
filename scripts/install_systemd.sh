#!/bin/bash
# 安装 yt2bl 订阅监控看门狗服务
# 注意：此脚本仅安装看门狗监控，不安装主服务（yt2bl.service/timer）
# 主服务需要单独配置

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 检查是否为root权限
if [ "$EUID" -eq 0 ]; then
    error "请不要使用root权限运行此脚本。服务将以当前用户身份运行。"
fi

# 检查systemd
if ! command -v systemctl &> /dev/null; then
    error "未找到systemd命令，此脚本仅支持systemd系统。"
fi

info "项目目录: $PROJECT_DIR"
info "当前用户: $USER"

# 复制服务文件
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

info "安装看门狗监控服务文件..."

# 仅安装看门狗服务
cp "$SCRIPT_DIR/yt2bl-monitor-watchdog.service" "$SERVICE_DIR/"
cp "$SCRIPT_DIR/yt2bl-monitor-watchdog.timer" "$SERVICE_DIR/"

# 替换路径
sed -i "s|User=bk|User=$USER|g" "$SERVICE_DIR/yt2bl-monitor-watchdog.service"
sed -i "s|WorkingDirectory=/home/bk/projects/yt2bl|WorkingDirectory=$PROJECT_DIR|g" "$SERVICE_DIR/yt2bl-monitor-watchdog.service"
sed -i "s|/home/bk/projects/yt2bl/.venv|$PROJECT_DIR/.venv|g" "$SERVICE_DIR/yt2bl-monitor-watchdog.service"
sed -i "s|/home/bk/projects/yt2bl/scripts/monitor_subscription.py|$PROJECT_DIR/scripts/monitor_subscription.py|g" "$SERVICE_DIR/yt2bl-monitor-watchdog.service"

info "重载 systemd 配置..."
systemctl --user daemon-reload

info "启用并启动看门狗定时任务..."
systemctl --user enable yt2bl-monitor-watchdog.timer
systemctl --user start yt2bl-monitor-watchdog.timer

echo ""
info "✅ 看门狗服务安装完成！"
echo ""
info "服务状态:"
echo "  看门狗定时任务: systemctl --user status yt2bl-monitor-watchdog.timer"
echo ""
info "日志查看:"
echo "  看门狗日志: journalctl --user -u yt2bl-monitor-watchdog -f"
echo ""
warn "注意: 如果使用持久化用户会话，请运行: loginctl enable-linger $USER"
warn "否则注销后定时任务将不会运行。"
