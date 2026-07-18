# YouTube to Bilibili 视频搬运工具（yt2bl）

将 YouTube 计算机科学相关视频搬运到 Bilibili 的自动化工具：搜索/下载 → LLM 字幕翻译（双语）→ 字幕嵌入 → 转载上传到 B 站（自动生成中文标题、标签、简介）。支持完整端到端工作流、两步工作流，以及订阅监控（由 crontab / systemd timer 定时触发）。

> **所有命令均为非交互式**（纯命令行参数驱动），适合脚本与定时任务自动化。

## 功能特性

- 🔍 **搜索与下载**：YouTube Data API（可选，无则 mock）+ yt-dlp 真实下载；DASH 1080p+ 自动合并；自动下载字幕与封面；CS 内容过滤与质量评分
- 🌐 **字幕翻译**：LLM 批量翻译为双语（英文 + 中文），格式校验与重试，翻译缓存支持**断点续传**
- 🎬 **字幕处理**：SRT ↔ ASS 转换（中英分别样式）、时间轴重叠修复、双语字幕硬编码嵌入（FFmpeg）
- 📤 **B 站上传**：转载上传（`copyright=2`、`source` = YouTube URL、含转载声明）；上传时由 LLM 生成中文标题（5–20 字）、标签（3–6 个）与简介
- 📡 **订阅监控**：一次性 cron/timer 驱动，单例锁（`.updating`）+ 看门狗 + 持久化历史，自动跳过已处理视频
- ⚙️ **配置与日志**：环境变量集中配置（Pydantic），分级日志

## 快速开始

> 完整安装步骤见 [INSTALL_GUIDE.md](INSTALL_GUIDE.md)，使用示例见 [example.md](example.md)，开发说明见 [CLAUDE.md](CLAUDE.md)。

**环境要求**：Python 3.9+（推荐 3.11+）、**FFmpeg**（合并 1080p+ 视频流与嵌入字幕所必需，须在 `PATH` 中）。

```bash
git clone git@github.com:LichKing-W/yt2bl.git
cd yt2bl

python3 -m venv .venv && source .venv/bin/activate
pip install -e .              # 注册 yt2bl 命令；可选: pip install -e ".[dev]"

cp .env.example .env          # 编辑 .env 填写 B 站认证 / OpenAI / 代理等
```

验证安装：

```bash
yt2bl --help
yt2bl --check-auth            # 检查 B 站认证是否有效（需先配好 .env 中的 BILIBILI_*）
```

## 常用命令

```bash
# 完整端到端：下载 → 翻译字幕 → 嵌入双语字幕 → 上传
yt2bl --full-workflow "https://www.youtube.com/watch?v=VIDEO_ID"

# 两步工作流：先准备（不上传），检查后再上传
yt2bl --prepare "https://www.youtube.com/watch?v=VIDEO_ID"
yt2bl --upload-folder "ChannelName|VIDEO_ID"

# 下载指定频道 / 视频
yt2bl --channel-id "@username" --max-videos 5
yt2bl --url "https://www.youtube.com/watch?v=VIDEO_ID"

# 字幕独立操作
yt2bl --translate-subs subs.en.srt     # 翻译为双语（生成 zh.srt）
yt2bl --convert-to-ass zh.srt          # SRT 转 ASS（双语分别样式）
yt2bl --embed-bilingual video.mp4 zh.srt
yt2bl --gen-description zh.srt         # 从字幕生成视频简介

# 批量下载（TSV: channel<TAB>max_videos）
yt2bl --batch scripts/author_videonum.txt
```

订阅监控（一次性，由定时器触发，频道列表写在 `youtuber.txt`）：

```bash
python -m src.subscription_monitor                # 单次检查并处理新视频
./scripts/run_subscription_monitor.sh             # 包装脚本（先校验配置）
```

## 配置

编辑 `.env`（示例见 `.env.example`），关键字段：

```env
# 下载
YOUTUBE_API_KEY=              # 可选；留空则使用 mock 数据
YOUTUBE_COOKIES_FILE=         # 推荐：Netscape 格式 cookies，绕过机器人检测
PROXY=                        # 按需，例如 http://127.0.0.1:7897（自动应用到所有 yt-dlp 操作）

# 上传到 B 站（必需）
BILIBILI_SESSDATA=
BILIBILI_BILI_JCT=
BILIBILI_DedeUserID=

# 字幕翻译（LLM；可指向 OpenAI / DeepSeek 等兼容端点）
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=

# 下载与编码
DOWNLOAD_PATH=./data
VIDEO_QUALITY=1080p
FFMPEG_HWACCEL=auto           # auto/nvenc/qsv/amf/videotoolbox/vaapi/none
FFMPEG_PRESET=fast

# 日志
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

获取 B 站认证：登录网页版 B 站 → F12 开发者工具 → Network → 任一请求 Headers 的 Cookie 中提取 `SESSDATA` / `bili_jct` / `DedeUserID`。

## 项目结构

```
yt2bl/
├── src/
│   ├── main.py                   # CLI 入口 (YouTubeToBilibili)
│   ├── subscription_monitor.py   # 订阅监控（一次性，cron/timer 触发）
│   ├── youtube/                  # models / searcher / downloader
│   ├── bilibili/                 # models / uploader / content_optimizer（标题/标签/简介）
│   ├── core/                     # video_processor / subtitle_processor（翻译/转换/嵌入）
│   └── utils/                    # config / logger / llm_client / fix_you_srt_tl
├── prompts/                      # LLM 提示词模板（运行时读取）
├── test/                         # 单元测试（pytest）
├── scripts/                      # 监控、看门狗、systemd / crontab 示例
├── data/                         # 视频存储（运行时生成）
├── logs/                         # 日志（运行时生成）
├── .env.example
├── pyproject.toml                # 项目配置与依赖
├── INSTALL_GUIDE.md / example.md / CLAUDE.md
└── README.md
```

每个视频生成独立子目录 `data/{YouTuber名}|{video_id}/`，内含视频、`zh.srt`（双语字幕）、`video_description.txt` 与封面。

## 工作流

- **完整工作流**（`--full-workflow`）：下载 → 翻译字幕 → 嵌入双语字幕 → 上传；成功后写入订阅历史并自动清理 `data/`（超过 10 个视频文件夹时全部删除）。
- **两步工作流**（`--prepare` + `--upload-folder`）：先准备好产出（不上传），人工检查后再上传。
- **订阅监控**：定时拉取 `youtuber.txt` 中每个频道最新 3 个视频，跳过已处理的，对新视频跑完整工作流。

> 工作流为**失败即停**：任一关键步骤失败都会中止，避免上传不完整内容。

## 故障排除

- **下载失败 / 被识别为机器人**：配置 `YOUTUBE_COOKIES_FILE`；网络受限时配置 `PROXY`；升级 `pip install -U yt-dlp`。
- **1080p 下载或字幕嵌入报错**：确认 `ffmpeg -version` 可用（DASH 流需 FFmpeg 合并独立视频/音频轨）。
- **字幕翻译失败**：确认 `OPENAI_API_KEY`；第三方端点需设 `OPENAI_BASE_URL` / `OPENAI_MODEL`；翻译支持断点续传，中断后重跑即可。
- **依赖/导入问题**：`pip install -e .`；确认已激活虚拟环境且 Python ≥ 3.9。

```bash
tail -f logs/app.log            # 实时日志
grep ERROR logs/app.log         # 仅错误
```

## 开发

```bash
pip install -e ".[dev]"                  # 安装开发工具
pytest test/ -v                          # 测试
ruff check --fix src/ && ruff format src/  # 代码检查 / 格式化
mypy src/                                # 类型检查
```

详见 [CLAUDE.md](CLAUDE.md)。

## 注意事项

- **版权与合规**：本工具仅供学习交流；请遵守 YouTube 与 B 站服务条款，尊重原创者版权，转载须标注来源。
- **频率控制**：合理控制下载/上传频率，避免触发平台限制。
- **认证更新**：B 站 Cookie 通常约 1 个月过期，需定期更新。
- **技术限制**：依赖稳定网络（可能需代理）；视频处理需足够磁盘空间；YouTube API 有配额限制。

## 许可证

本项目采用 [MIT License](LICENSE) 开源。

## 免责声明

本工具仅供学习和研究使用。使用者需自行承担使用本工具的法律责任，包括但不限于版权侵权、违反平台服务条款等风险。开发者不对使用本工具产生的任何后果承担责任。

---

**⚠️ 重要提醒**：请务必遵守相关法律法规和平台规则，尊重知识产权，合理使用本工具。
