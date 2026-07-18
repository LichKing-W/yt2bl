# 安装指南

本指南描述从零开始安装并运行 `yt2bl`（YouTube → Bilibili 搬运工具）的完整流程。

## 环境要求

| 依赖 | 版本 / 说明 | 用途 |
|------|-------------|------|
| Python | **3.9+**（推荐 3.11+） | 运行时 |
| FFmpeg | 任意较新版本，需在 `PATH` 中 | 合并 1080p+ 的 DASH 视频流、把双语字幕硬编码进视频 |
| Git | 任意版本 | 克隆仓库 |

> 字幕嵌入（`--full-workflow` / `--prepare` 的第 3 步）**必须**有 FFmpeg；没有它，1080p 以上的下载和字幕嵌入都会失败。

安装 FFmpeg：

```bash
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg
```

## 1. 克隆仓库

```bash
git clone git@github.com:LichKing-W/yt2bl.git
cd yt2bl
```

## 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

## 3. 安装项目（可编辑模式）

项目以 `pyproject.toml` 为唯一依赖来源，并提供了 `yt2bl` 命令行入口（`src.main:cli`）。

```bash
pip install -e .
```

这一步会安装全部运行时核心依赖（包含 `yt-dlp`、`rich`、`pydantic`、`bilibili-api-python`、`openai`、`aiohttp` 等）并注册 `yt2bl` 命令。

### 可选附加依赖

按需安装（`pyproject.toml` 的 `[project.optional-dependencies]`）：

```bash
pip install -e ".[dev]"      # ruff、pytest、mypy 等开发工具（参与开发时推荐）
pip install -e ".[video]"    # moviepy，额外的视频处理能力
pip install -e ".[bilibili]" # 显式锁定 bilibili-api-python 版本（核心已含，一般无需）
pip install -e ".[translate]"# 显式锁定 openai 版本（核心已含，一般无需）
```

也可以一次性装齐：`pip install -e ".[dev,video]"`。

### 使用 uv（可选）

仓库附带 `uv.lock`，如果你使用 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync --extra dev          # 按 uv.lock 创建环境并安装
uv run yt2bl --help
```

> `pip install -e .` 与 `uv sync` 二选一即可，不要在同一环境混用。

## 4. 配置 `.env`

复制示例配置并按需填写：

```bash
cp .env.example .env
```

关键字段（详见 `.env.example` 内注释）：

- **下载相关**
  - `YOUTUBE_API_KEY`（可选）真实搜索；留空则回退到 mock 数据
  - `YOUTUBE_COOKIES_FILE`（推荐）Netscape 格式 cookies 文件，绕过 YouTube 机器人检测
  - `PROXY`（按需）HTTP/HTTPS 代理，例如 `http://127.0.0.1:7897`；代理会自动应用到所有 yt-dlp 操作，**无需**额外设置 `HTTP_PROXY` 环境变量
- **上传到 B 站（必需）**
  - `BILIBILI_SESSDATA`、`BILIBILI_BILI_JCT`、`BILIBILI_DedeUserID`
- **字幕翻译（LLM）**
  - `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`（默认 `gpt-4o-mini`，可指向 DeepSeek 等兼容端点）
- **编码**
  - `FFMPEG_HWACCEL`（`auto` / `nvenc` / `qsv` / `amf` / `videotoolbox` / `vaapi` / `none`）
  - `FFMPEG_PRESET`（`fast` / `medium` / `slow` …）
- **下载/日志**
  - `DOWNLOAD_PATH`（默认 `./data`）、`VIDEO_QUALITY`（默认 `1080p`）、`LOG_FILE`（默认 `./logs/app.log`）

获取 B 站认证信息：登录网页版 B 站 → F12 开发者工具 → Network → 任一请求的 Headers → Cookie 中提取 `SESSDATA` / `bili_jct` / `DedeUserID`。

## 5. 验证安装

```bash
# 入口可用
yt2bl --help

# 或等价的模块调用
python -m src.main --help

# 检查 B 站认证是否有效（需要先配置好 .env 中的 BILIBILI_* 三项）
python -m src.main --check-auth
```

看到帮助输出即说明安装成功。`--check-auth` 能返回用户名/等级说明 B 站 Cookie 配置正确。

## 6. 常用命令

```bash
# 完整端到端：下载 → 翻译字幕 → 嵌入双语字幕 → 上传到 B 站
yt2bl --full-workflow "https://www.youtube.com/watch?v=VIDEO_ID"

# 两步工作流：先准备（不上传），再上传
yt2bl --prepare "https://www.youtube.com/watch?v=VIDEO_ID"
yt2bl --upload-folder "ChannelName|VIDEO_ID"

# 下载指定频道
yt2bl --channel-id "@username" --max-videos 5

# 字幕相关独立操作
yt2bl --translate-subs path/to/subs.srt
yt2bl --convert-to-ass path/to/subs.srt
yt2bl --embed-bilingual video.mp4 bilingual_subs.srt
yt2bl --gen-description bilingual_subs.srt
```

> 所有命令均为**非交互式**（纯命令行参数驱动），适合脚本/cron 自动化。

## 常见问题

### 下载失败 / 被识别为机器人
- 配置 `YOUTUBE_COOKIES_FILE`（Netscape 格式）；
- 网络受限时配置 `PROXY`；
- 确认 `yt-dlp` 已随 `pip install -e .` 安装并可升级：`pip install -U yt-dlp`。

### 1080p 下载或字幕嵌入报错
- 确认 `ffmpeg` 在 `PATH` 中：`ffmpeg -version`；
- DASH 流（1080p+）需要 FFmpeg 合并独立的视频/音频轨。

### 字幕翻译失败
- 确认 `OPENAI_API_KEY` 已设置；
- 如使用第三方/兼容端点，设置 `OPENAI_BASE_URL` 与 `OPENAI_MODEL`；
- 翻译支持断点续传（缓存文件 `data/{author}|{id}/zh.cache.json`），中断后重跑即可继续。

### `pip install` 连接超时
- 使用国内镜像：`pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple`；
- 或配置代理：`pip` 走 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量。

### 运行订阅监控（可选）
订阅监控是一次性命令，由 crontab/systemd timer 定时触发，详见 `CLAUDE.md` 的「Subscription Monitoring」与 `scripts/crontab.example`、`scripts/install_systemd.sh`。
