# YouTube to Bilibili 视频搬运工具 - 使用说明

## 项目简介

YouTube to Bilibili 是一个自动化视频搬运工具，专门用于将YouTube上的计算机科学相关视频下载并搬运到Bilibili平台。该工具支持智能搜索、视频下载、格式转换和自动上传等功能。

## 快速开始

### 1. 环境要求

- **Python**: 3.9 或更高版本
- **操作系统**: Linux, macOS, Windows
- **网络**: 稳定的互联网连接（可能需要代理访问YouTube）

### 2. 一键安装

```bash
# 克隆项目
git clone <repository-url>
cd youtube-projects

# 运行安装脚本
chmod +x setup.sh
./setup.sh
```

### 3. 手动安装

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -e .

# 3. 创建配置文件
cp .env.example .env

# 4. 创建必要目录
mkdir -p data logs config
```

## 配置说明

### 环境变量配置

编辑 `.env` 文件，配置以下选项：

```env
# YouTube API配置（可选，用于真实搜索）
YOUTUBE_API_KEY=your_youtube_api_key_here

# Bilibili认证信息（上传功能必需）
BILIBILI_SESSDATA=your_sessdata_here
BILIBILI_BILI_JCT=your_bili_jct_here
BILIBILI_DedeUserID=your_dedeuserid_here

# 下载配置
DOWNLOAD_PATH=./data
MAX_VIDEO_SIZE_MB=500
VIDEO_QUALITY=720p

# 上传配置
UPLOAD_COOLDOWN_HOURS=2
AUTO_PUBLISH=false

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

### 获取配置信息

#### YouTube API密钥（可选）
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 YouTube Data API v3
4. 创建API密钥并复制到配置文件

#### Bilibili认证信息（上传必需）
1. 登录Bilibili网页版
2. 打开浏览器开发者工具 (F12)
3. 在Network标签页刷新页面
4. 找到任意请求，在Headers中找到Cookie
5. 提取以下值：
   - `SESSDATA`
   - `bili_jct`
   - `DedeUserID`

## 使用方法

### 1. 基本使用

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行主程序（搜索热门视频）
python -m src.main

# 或使用命令行工具
yt2bl
```

### 2. 指定参数运行

```bash
# 限制下载数量
python -m src.main --max-videos 5

# 下载指定URL的视频
python -m src.main --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 下载指定频道的视频
python -m src.main --channel-id "@username"
python -m src.main --channel-id "UC1234567890"
```

### 3. 程序化使用

```python
import asyncio
from src.main import YouTubeToBilibili

async def main():
    # 创建应用实例
    app = YouTubeToBilibili()
    
    # 搜索并下载视频
    videos = await app.search_and_download(max_videos=5)
    
    # 处理下载结果
    for video in videos:
        print(f"已下载: {video.title}")
        if hasattr(video, 'downloaded_path'):
            print(f"文件路径: {video.downloaded_path}")

# 运行程序
asyncio.run(main())
```

## 功能特性

### ✅ 已实现功能

1. **YouTube视频搜索**
   - 智能搜索计算机科学相关视频
   - 支持关键词过滤和质量评分
   - 自动去重和排序

2. **视频下载**
   - 使用yt-dlp进行真实视频下载
   - 支持多种视频质量选择（480p, 720p, 1080p）
   - 自动下载字幕和封面
   - 文件大小限制保护

3. **视频处理**
   - 自动视频格式转换
   - 字幕处理和翻译
   - 封面优化

4. **用户界面**
   - Rich库美化的命令行界面
   - 实时下载进度显示
   - 交互式视频选择

5. **配置管理**
   - 灵活的环境变量配置
   - Pydantic数据验证
   - 完善的日志系统

### 🚧 开发中功能

1. **Bilibili上传**
   - 自动登录和认证
   - 视频上传和发布
   - 内容优化和标签生成

2. **批量处理**
   - 任务队列管理
   - 定时任务支持
   - 断点续传

## 使用示例

### 示例1：搜索并下载热门视频

```bash
$ python -m src.main --max-videos 3

🚀 YouTube to Bilibili 视频搬运工具
==================================================
✅ 配置检查通过
下载目录: ./data
视频质量: 720p
最大文件大小: 500MB

🔍 正在搜索计算机领域热门视频...

搜索结果 (共3个):
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┓
┃ 序号 ┃ 标题                                   ┃ 频道               ┃ 观看/点赞       ┃ 评分 ┃ 发布时间 ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━┩
│ 1  │ Python Tutorial for Beginners         │ Programming Hub    │ 1200k/45k     │ 8.5  │ 12-20    │
│ 2  │ Machine Learning Explained            │ Tech Academy       │ 890k/32k      │ 7.8  │ 12-18    │
│ 3  │ JavaScript ES6 Features               │ Code Masters       │ 650k/28k      │ 7.2  │ 12-15    │
└────┴────────────────────────────────────────┴────────────────────┴───────────────┴──────┴──────────┘

请选择要下载的视频（输入序号，多个用逗号分隔，或输入 'all' 下载全部）[1]: 1,2

📥 下载中 (1/2): Python Tutorial for Beginners...
✅ 下载完成: Python_Tutorial_for_Beginners_[abc123].mp4

📥 下载中 (2/2): Machine Learning Explained...
✅ 下载完成: Machine_Learning_Explained_[def456].mp4

🎉 成功下载 2 个视频

📋 下载摘要:
1. Python Tutorial for Beginners...
   文件: Python_Tutorial_for_Beginners_[abc123].mp4 (45.2MB)
2. Machine Learning Explained...
   文件: Machine_Learning_Explained_[def456].mp4 (67.8MB)

🎊 程序执行完成！
```

### 示例2：下载指定URL视频

```bash
$ python -m src.main --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

🚀 YouTube to Bilibili 视频搬运工具
==================================================
✅ 配置检查通过

📥 正在下载视频...
✅ 下载完成: Rick_Astley_Never_Gonna_Give_You_Up_[dQw4w9WgXcQ].mp4 (30.9MB)
```

### 示例3：下载频道视频

```bash
$ python -m src.main --channel-id "@ProgrammingWithMosh" --max-videos 5

🚀 YouTube to Bilibili 视频搬运工具
==================================================
🔍 正在获取频道 @ProgrammingWithMosh 的视频...

# 显示频道视频列表，用户选择下载...
```

## 项目结构

```
youtube-projects/
├── src/                          # 源代码目录
│   ├── __init__.py
│   ├── main.py                   # 主程序入口
│   ├── __main__.py               # 模块运行入口
│   ├── youtube/                  # YouTube相关模块
│   │   ├── __init__.py
│   │   ├── models.py             # 数据模型
│   │   ├── searcher.py           # 视频搜索
│   │   └── downloader.py         # 视频下载
│   ├── bilibili/                 # Bilibili相关模块
│   │   ├── __init__.py
│   │   ├── uploader.py           # 视频上传
│   │   └── content_optimizer.py  # 内容优化
│   ├── core/                     # 核心处理模块
│   │   ├── __init__.py
│   │   ├── video_processor.py    # 视频处理
│   │   └── subtitle_processor.py # 字幕处理
│   └── utils/                    # 工具模块
│       ├── __init__.py
│       ├── config.py             # 配置管理
│       └── logger.py             # 日志管理
├── test/                         # 测试文件
│   ├── test_youtube_searcher.py
│   └── test_video_processor.py
├── data/                         # 视频存储目录
├── logs/                         # 日志文件目录
├── scripts/                      # 脚本文件
│   ├── run_dev.sh               # 开发运行脚本
│   ├── quick_test.sh            # 快速测试脚本
│   └── test_minimal.sh          # 最小测试脚本
├── config/                       # 配置文件目录
├── .env                         # 环境变量配置
├── .env.example                 # 环境变量示例
├── pyproject.toml               # 项目配置
├── setup.py                     # 安装脚本
├── setup.sh                     # 一键安装脚本
├── README.md                    # 项目说明
├── PROJECT_PLAN.md              # 项目规划
├── PROJECT_STATUS.md            # 项目状态
└── example.md                   # 使用说明（本文件）
```

## 故障排除

### 常见问题

1. **搜索无结果**
   ```
   问题：运行程序后显示"未找到符合条件的视频"
   解决：
   - 检查网络连接
   - 如果没有配置YouTube API，程序会使用模拟数据
   - 确认API密钥配置正确
   ```

2. **下载失败**
   ```
   问题：视频下载过程中出现错误
   解决：
   - 确认已安装 yt-dlp: pip install yt-dlp
   - 检查网络连接和代理设置
   - 查看日志文件获取详细错误信息: tail -f logs/app.log
   - 某些视频可能有地区限制或需要认证
   ```

3. **依赖问题**
   ```
   问题：导入模块失败或缺少依赖
   解决：
   - 重新安装依赖: pip install -e .
   - 确认Python版本 >= 3.9
   - 激活虚拟环境: source .venv/bin/activate
   ```

4. **配置问题**
   ```
   问题：程序无法读取配置或配置验证失败
   解决：
   - 检查 .env 文件是否存在
   - 确认配置格式正确
   - 查看配置示例: cat .env.example
   ```

### 日志查看

```bash
# 查看完整日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log

# 查看最近的日志
tail -n 50 logs/app.log
```

### 调试模式

```bash
# 设置调试级别
export LOG_LEVEL=DEBUG
python -m src.main

# 或在 .env 文件中设置
LOG_LEVEL=DEBUG
```

## 开发和测试

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
pytest test/ -v

# 运行特定测试
pytest test/test_youtube_searcher.py -v

# 快速功能测试
./scripts/quick_test.sh
```

### 代码格式化

```bash
# 使用ruff检查和格式化
ruff check --fix src/
ruff format src/

# 类型检查
mypy src/
```

### 开发环境运行

```bash
# 使用开发脚本
./scripts/run_dev.sh

# 或直接运行
export PYTHONPATH="$(pwd):$PYTHONPATH"
python -m src.main
```

## 注意事项

### 版权和合规
- **版权尊重**: 本工具仅供学习和交流使用，请尊重原创者版权
- **服务条款**: 请遵守YouTube和Bilibili的服务条款
- **转载声明**: 建议获得原作者许可后再进行转载，并标注视频来源
- **内容审核**: 确保转载内容符合平台规范和法律法规

### 使用建议
- **频率控制**: 合理控制下载和上传频率，避免触发平台限制
- **内容质量**: 做好内容筛选和审核，确保转载内容质量
- **认证更新**: 定期更新Bilibili认证信息，避免认证过期
- **监控日志**: 定期查看日志文件，及时处理异常情况

### 技术限制
- **网络依赖**: 依赖稳定的网络环境，可能需要代理访问YouTube
- **存储空间**: 视频处理需要足够的本地存储空间
- **处理时间**: 大文件下载和处理可能耗时较长
- **API限制**: YouTube API有请求频率和配额限制

## 更新日志

### v0.1.0 (当前版本)
- ✅ 实现YouTube视频搜索和下载
- ✅ 支持真实视频下载（yt-dlp集成）
- ✅ 完善的配置管理和日志系统
- ✅ Rich库美化的用户界面
- ✅ 基础的视频处理功能
- 🚧 Bilibili上传功能开发中

### 计划功能
- 📋 Web界面开发
- 📋 批量处理优化
- 📋 定时任务支持
- 📋 视频质量分析
- 📋 数据统计和报告

## 许可证

本项目采用 MIT 许可证。详情请查看 [LICENSE](LICENSE) 文件。

## 免责声明

本工具仅供学习和研究使用。使用者需要自行承担使用本工具的法律责任，包括但不限于版权侵权、违反平台服务条款等风险。开发者不对使用本工具产生的任何后果承担责任。

---

**⚠️ 重要提醒**: 请务必遵守相关法律法规和平台规则，尊重知识产权，合理使用本工具。

**📞 技术支持**: 如遇问题，请查看日志文件或提交Issue到项目仓库。