# YouTube to Bilibili 视频搬运工具 - 使用示例

> 本文件聚焦**实际使用方式与命令示例**。安装细节见 [INSTALL_GUIDE.md](INSTALL_GUIDE.md)，完整开发说明见 [CLAUDE.md](CLAUDE.md)。

## 项目简介

将 YouTube 计算机科学相关视频搬运到 Bilibili 的自动化工具：搜索/下载 → LLM 字幕翻译 → 双语字幕嵌入 → 转载上传到 B 站（自动生成中文标题、标签、简介）。支持完整端到端工作流、两步工作流，以及订阅监控（一次性、由 crontab/systemd timer 触发）。

**所有命令均为非交互式（纯命令行参数驱动）**，适合脚本与定时任务自动化。

## 环境与安装

- **Python** 3.9+（推荐 3.11+）
- **FFmpeg**（必须在 `PATH` 中，用于合并 1080p+ 视频流和嵌入字幕）

```bash
git clone git@github.com:LichKing-W/yt2bl.git
cd yt2bl
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # 注册 yt2bl 命令；可选: pip install -e ".[dev]"
cp .env.example .env        # 然后编辑 .env 填写配置
```

详见 [INSTALL_GUIDE.md](INSTALL_GUIDE.md)。

## 配置 `.env`

关键字段（完整列表与注释见 `.env.example`）：

```env
# 下载（可选 API；推荐 cookies 绕过机器人检测；按需配代理）
YOUTUBE_API_KEY=
YOUTUBE_COOKIES_FILE=
PROXY=                       # 例如 http://127.0.0.1:7897，自动应用到所有 yt-dlp 操作

# 上传到 B 站（必需）
BILIBILI_SESSDATA=
BILIBILI_BILI_JCT=
BILIBILI_DedeUserID=

# 字幕翻译（LLM，可指向 OpenAI / DeepSeek 等兼容端点）
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=

# 下载与编码
DOWNLOAD_PATH=./data
VIDEO_QUALITY=1080p
FFMPEG_HWACCEL=auto          # auto/nvenc/qsv/amf/videotoolbox/vaapi/none
FFMPEG_PRESET=fast

# 日志
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

获取 B 站认证：登录网页版 B 站 → F12 开发者工具 → Network → 任一请求 Headers 的 Cookie 中提取 `SESSDATA` / `bili_jct` / `DedeUserID`。

## 使用示例

每个视频会生成独立子目录 `data/{YouTuber名}|{video_id}/`，内含视频、`zh.srt`（双语字幕）、`video_description.txt`、封面等。

### 示例 1：完整端到端工作流（推荐）

一条命令完成：下载 → 翻译字幕 → 嵌入双语字幕 → 上传。

```bash
yt2bl --full-workflow "https://www.youtube.com/watch?v=VIDEO_ID"
```

示例输出（节选，`步骤 1/5 … 5/5`）：

```
🚀 YouTube 到 Bilibili 完整工作流
==================================================
✅ 配置检查通过

📥 步骤 1/5: 获取视频信息并下载
✅ 视频信息获取成功: <视频标题>
✅ 视频下载完成: <title>.mp4

🌐 步骤 2/5: 翻译字幕
📝 找到字幕文件: en.srt
✅ 字幕翻译完成: zh.srt

🎬 步骤 3/5: 嵌入双语字幕到视频
✅ 字幕嵌入完成: <title>.mp4

📤 步骤 4/5: 上传到 Bilibili
标题: 中文标题 | YouTuber名
✅ 上传成功!

🎊 步骤 5/5: 完成
   BV 号: BV1xxxxxxxx
   链接: https://www.bilibili.com/video/BV1xxxxxxxx
🎊 完整工作流执行完成！
```

> 上传成功后会自动：把 video_id 写入订阅历史（防重复处理），并在 `data/` 下视频文件夹超过 10 个时清理。

### 示例 2：两步工作流（先准备，再上传）

适合先检查产出再上传：

```bash
# 第 1 步：下载 + 翻译 + 修复时间轴 + 嵌入字幕 + 生成简介（不上传）
yt2bl --prepare "https://www.youtube.com/watch?v=VIDEO_ID"
# 完成后会打印文件夹名和对应的上传命令，例如：
#   yt2bl --upload-folder "ChannelName|VIDEO_ID"

# 第 2 步：上传准备好的文件夹（直接上传，无确认提示）
yt2bl --upload-folder "ChannelName|VIDEO_ID"
```

### 示例 3：下载频道视频

```bash
# 支持 @username、UC...ID 或完整频道 URL，自动下载前 N 个（非交互）
yt2bl --channel-id "@username" --max-videos 5
yt2bl --channel-id "UC1234567890" --max-videos 3
```

### 示例 4：字幕独立操作

```bash
# 翻译英文字幕为双语（生成 zh.srt，支持断点续传）
yt2bl --translate-subs path/to/subs.en.srt

# SRT 转 ASS（双语分别样式）
yt2bl --convert-to-ass path/to/zh.srt

# 把双语字幕硬编码进视频
yt2bl --embed-bilingual video.mp4 zh.srt

# 从双语字幕生成视频简介
yt2bl --gen-description zh.srt
```

### 示例 5：订阅监控（定时搬运）

监控器是**一次性**命令，由 crontab 或 systemd timer 定时触发；频道列表写在 `youtuber.txt`（每行一个 `@username` / `UC...ID` / 完整 URL）。

```bash
# 单次检查：对每个频道取最新 3 个视频，跳过已处理的，对新视频跑完整工作流
python -m src.subscription_monitor

# 也可禁用翻译/嵌入：
python -m src.subscription_monitor --no-translate --no-embed

# 包装脚本（先校验 .env / youtuber.txt / B 站配置，再转发参数）
./scripts/run_subscription_monitor.sh
```

防卡死看门狗（终止超过阈值的监控进程并清理 `.updating` 锁）：

```bash
python scripts/monitor_subscription.py --dry-run      # 仅检查
python scripts/monitor_subscription.py --timeout 6    # 超过 6 小时则终止
```

部署方式见 `scripts/crontab.example`、`scripts/install_systemd.sh`、`scripts/monitor_README.md`。

### 示例 6：程序化使用

```python
import asyncio
from src.main import YouTubeToBilibili

async def main():
    # 创建实例；如需上传/翻译，按需传参
    app = YouTubeToBilibili(enable_upload=True, translate_subs=True)

    # 按频道搜索并下载（非交互，下载全部）
    videos = await app.search_and_download_by_channel("@username", max_videos=5)
    for v in videos:
        print(f"已下载: {v.title}")
        if hasattr(v, "downloaded_path"):
            print(f"  文件: {v.downloaded_path}")

    # 完整工作流（下载→翻译→嵌入→上传）
    await app.run_full_workflow("https://www.youtube.com/watch?v=VIDEO_ID")

asyncio.run(main())
```

## 功能特性（均已实现）

- **搜索/下载**：YouTube Data API（可选，无则 mock）+ yt-dlp 真实下载；DASH 1080p+ 合并；自动下载字幕与封面；CS 内容过滤与质量评分
- **字幕翻译**：LLM 批量翻译为双语（英文+中文），格式校验+重试，翻译缓存支持断点续传
- **字幕处理**：SRT↔ASS 转换（中英分样式）、时间轴重叠修复、双语字幕硬编码嵌入（FFmpeg）
- **B 站上传**：转载上传（`copyright=2`，`source`=YouTube URL，含转载声明）；上传时由 LLM 生成中文标题（5–20 字）、标签（3–6 个）、简介
- **订阅监控**：一次性 cron/timer 驱动，单例锁（`.updating`）+ 看门狗 + 持久化历史
- **配置/日志**：环境变量集中配置（Pydantic），分级日志

## 项目结构

```
yt2bl/
├── src/
│   ├── __init__.py
│   ├── __main__.py               # python -m src 入口
│   ├── main.py                   # CLI 入口 (YouTubeToBilibili)
│   ├── subscription_monitor.py   # 订阅监控（一次性，cron/timer 触发）
│   ├── youtube/
│   │   ├── models.py             # YouTubeVideo 数据模型
│   │   ├── searcher.py           # 搜索（频道/热门）
│   │   └── downloader.py         # 下载（yt-dlp）
│   ├── bilibili/
│   │   ├── models.py             # BilibiliVideo 模型
│   │   ├── uploader.py           # B 站上传
│   │   └── content_optimizer.py  # 标题/标签/简介生成（LLM）
│   ├── core/
│   │   ├── video_processor.py    # 视频处理
│   │   └── subtitle_processor.py # 字幕翻译/转换/嵌入
│   └── utils/
│       ├── config.py             # 配置（.env）
│       ├── logger.py             # 日志
│       ├── llm_client.py         # 共享 OpenAI 客户端
│       └── fix_you_srt_tl.py     # 字幕时间轴修复工具
├── prompts/                      # LLM 提示词模板（运行时读取）
│   ├── translate.md
│   ├── description.md
│   ├── generate_title.md
│   └── generate_tags.md
├── test/                         # 单元测试（pytest）
├── scripts/                      # 运维脚本（监控、看门狗、systemd/crontab 示例）
├── data/                         # 视频存储（运行时生成，.gitignore）
├── logs/                         # 日志（运行时生成，.gitignore）
├── .env.example                  # 环境变量示例（复制为 .env，.gitignore）
├── youtuber.txt                  # 订阅频道列表（用户创建，.gitignore）
├── pyproject.toml                # 项目配置与依赖
├── uv.lock                       # uv 锁定文件
├── CLAUDE.md                     # 开发指南
├── INSTALL_GUIDE.md              # 安装指南
├── README.md                     # 项目说明
└── example.md                    # 使用示例（本文件）
```

## 故障排除

1. **下载失败 / 被识别为机器人**
   - 配置 `YOUTUBE_COOKIES_FILE`（Netscape 格式）
   - 网络受限时配置 `PROXY`
   - 升级 yt-dlp：`pip install -U yt-dlp`

2. **1080p 下载或字幕嵌入报错**
   - 确认 `ffmpeg -version` 可用；DASH 流需 FFmpeg 合并独立视频/音频轨

3. **字幕翻译失败**
   - 确认 `OPENAI_API_KEY` 已配置；第三方端点需设 `OPENAI_BASE_URL` / `OPENAI_MODEL`
   - 翻译支持断点续传（缓存 `data/{author}|{id}/zh.cache.json`），中断后重跑即可继续

4. **依赖/导入问题**
   - 重新安装：`pip install -e .`
   - 确认已激活虚拟环境且 Python ≥ 3.9

### 查看日志

```bash
tail -f logs/app.log            # 实时日志
grep ERROR logs/app.log         # 仅错误
LOG_LEVEL=DEBUG python -m src.main   # 或在 .env 中设置 LOG_LEVEL=DEBUG
```

## 开发与测试

```bash
pip install -e ".[dev]"         # 安装开发工具
pytest test/ -v                 # 全部测试
pytest test/test_subtitle_translation.py -v   # 单个测试文件
ruff check --fix src/ && ruff format src/     # 代码检查/格式化
mypy src/                       # 类型检查
```

## 注意事项

- **版权与合规**：本工具仅供学习交流；请遵守 YouTube 与 B 站服务条款，尊重原创者版权，转载须标注来源
- **频率控制**：合理控制下载/上传频率，避免触发平台限制
- **认证更新**：B 站 Cookie 通常约 1 个月过期，需定期更新
- **技术限制**：依赖稳定网络（可能需代理）；视频处理需足够磁盘空间；YouTube API 有配额限制

## 许可证

本项目采用 MIT 许可证。详情见 [LICENSE](LICENSE)。

## 免责声明

本工具仅供学习和研究使用。使用者需自行承担使用本工具的法律责任，包括但不限于版权侵权、违反平台服务条款等风险。开发者不对使用本工具产生的任何后果承担责任。

---

**⚠️ 重要提醒**：请务必遵守相关法律法规和平台规则，尊重知识产权，合理使用本工具。
