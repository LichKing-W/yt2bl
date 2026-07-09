# Subscription 监控看门狗

防止 subscription 进程在嵌入字幕等耗时操作中卡住，阻塞后续运行。

## 问题说明

subscription 脚本每小时运行一次，但有时会在嵌入字幕部分卡住长达数小时，导致：
1. 当前进程占用资源
2. `.updating` 锁文件存在，阻止新的实例启动
3. 新视频无法被及时处理

## 解决方案

监控脚本定期检查 subscription 进程运行时长：
- 如果超过阈值（默认 6 小时），则终止进程
- 删除 `.updating` 锁文件
- 允许新的实例正常启动

## 文件说明

| 文件 | 说明 |
|------|------|
| `monitor_subscription.py` | 监控脚本，检查并终止超时进程 |
| `yt2bl-monitor-watchdog.service` | 看门狗服务的 systemd 配置 |
| `yt2bl-monitor-watchdog.timer` | 看门狗定时器（每小时检查） |
| `install_systemd.sh` | 自动安装脚本（仅安装看门狗） |

**注意**: 此脚本假设你已经配置了主服务（`yt2bl.service`/`yt2bl.timer`），只负责安装看门狗监控。

## 安装（systemd）

```bash
# 运行安装脚本（仅安装看门狗服务）
./scripts/install_systemd.sh

# 如果注销后需要定时任务继续运行，执行：
loginctl enable-linger $USER
```

## 手动测试

```bash
# 检查当前状态（不执行操作）
python scripts/monitor_subscription.py --dry-run

# 检查并终止超时进程
python scripts/monitor_subscription.py

# 自定义超时时间（3小时）
python scripts/monitor_subscription.py --timeout 3
```

## 管理命令

```bash
# 查看定时器状态
systemctl --user status yt2bl.timer  # 主服务
systemctl --user status yt2bl-monitor-watchdog.timer  # 看门狗

# 查看日志
journalctl --user -u yt2bl -f
journalctl --user -u yt2bl-monitor-watchdog -f

# 停止定时任务
systemctl --user stop yt2bl-monitor-watchdog.timer

# 禁用自动启动
systemctl --user disable yt2bl-monitor-watchdog.timer

# 重新加载配置（修改.service文件后）
systemctl --user daemon-reload
systemctl --user restart yt2bl-monitor-watchdog.timer
```

## 配置说明

### 主服务定时器 (yt2bl.timer)
- **频率**: 每小时（整点）
- **服务**: yt2bl.service → `subscription_monitor run`

### 看门狗定时器 (yt2bl-monitor-watchdog.timer)
- **频率**: 每小时（与主服务同步）
- **超时阈值**: 6小时
- **行为**: 超时后先 SIGTERM 优雅终止，30秒后仍运行则 SIGKILL

修改超时时间，编辑 `yt2bl-monitor-watchdog.service`:
```ini
ExecStart=.../python .../monitor_subscription.py --timeout 3  # 改为3小时
```
