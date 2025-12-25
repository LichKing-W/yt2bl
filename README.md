# YouTube to Bilibili 视频搬运工具

一个自动将YouTube计算机领域热门视频搬运到Bilibili平台的Python工具。

## 功能特性

- 🔍 **智能搜索**: 自动搜索计算机领域热门YouTube视频
- ⬇️ **视频下载**: 支持多种质量选择，自动下载字幕和封面
- 🎬 **视频处理**: 自动优化视频格式以适配B站要求
- 📝 **内容优化**: 智能翻译标题、描述，生成合适的标签
- 🚀 **自动上传**: 支持一键上传到B站，包含转载声明
- 📊 **质量评分**: 基于观看量、互动率等指标评估视频质量

## 快速开始

### 一键安装

```bash
# 克隆项目
git clone <repository-url>
cd youtube-projects

# 运行安装脚本
./setup.sh
```

### 手动安装

1. **环境要求**
   - Python 3.9+
   - FFmpeg (可选，用于视频处理)

2. **安装步骤**
```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .

# 复制配置文件
cp .env.example .env
```

3. **运行程序**
```bash
# 基本使用
python -m src.main

# 或使用命令行工具
yt2bl

# 指定下载数量
python -m src.main --max-videos 5

# 下载指定视频
python -m src.main --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 配置说明

编辑 `.env` 文件配置以下选项：

```env
# YouTube API配置（可选，用于真实搜索）
YOUTUBE_API_KEY=your_youtube_api_key

# Bilibili认证信息（上传必需）
BILIBILI_SESSDATA=your_sessdata
BILIBILI_BILI_JCT=your_bili_jct
BILIBILI_DedeUserID=your_dedeuserid

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
2. 创建项目并启用YouTube Data API v3
3. 创建API密钥并复制到配置文件

#### B站认证信息（上传必需）
1. 登录B站网页版
2. 打开浏览器开发者工具 (F12)
3. 在Network标签页刷新页面
4. 找到任意请求，在Headers中找到Cookie
5. 提取以下值：
   - `SESSDATA`
   - `bili_jct`
   - `DedeUserID`

## 项目结构

```
youtube-projects/
├── src/
│   ├── youtube/          # YouTube相关模块
│   │   ├── models.py      # 数据模型
│   │   ├── searcher.py    # 视频搜索
│   │   └── downloader.py  # 视频下载
│   ├── bilibili/          # B站相关模块（开发中）
│   ├── core/              # 核心处理模块（开发中）
│   ├── utils/             # 工具模块
│   │   ├── config.py      # 配置管理
│   │   └── logger.py      # 日志管理
│   └── main.py            # 主程序入口
├── data/                  # 视频存储目录
├── logs/                  # 日志文件
├── .env                   # 配置文件
├── setup.sh              # 安装脚本
└── README.md             # 说明文档
```

## 使用示例

### 基本搜索和下载

```bash
# 搜索并下载5个视频
python -m src.main --max-videos 5
```

程序会：
1. 搜索计算机领域热门视频
2. 显示搜索结果表格
3. 让用户选择要下载的视频
4. 下载选中的视频到 `data/` 目录

### 下载指定视频

```bash
# 下载指定URL的视频
python -m src.main --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 程序化使用

```python
import asyncio
from src.main import YouTubeToBilibili

async def main():
    app = YouTubeToBilibili()
    
    # 搜索和下载
    videos = await app.search_and_download(max_videos=5)
    
    # 处理下载的视频
    for video in videos:
        print(f"已下载: {video.title}")
        if hasattr(video, 'downloaded_path'):
            print(f"文件路径: {video.downloaded_path}")

asyncio.run(main())
```

## 开发状态

### ✅ 已完成功能
- YouTube视频搜索（支持API和模拟模式）
- 视频信息提取和质量评分
- 视频下载（支持yt-dlp和模拟模式）
- 配置管理和日志系统
- 命令行界面和进度显示

### 🚧 开发中功能
- B站视频上传
- 视频格式转换和处理
- 字幕处理和翻译
- 内容优化和标签生成
- 自动化工作流

### 📋 计划功能
- Web界面
- 批量处理
- 定时任务
- 视频质量分析
- 数据统计和报告

## 故障排除

### 常见问题

1. **搜索无结果**
   - 检查网络连接
   - 如果没有配置YouTube API，程序会使用模拟数据
   - 确认API密钥配置正确

2. **下载失败**
   - 确认已安装 `yt-dlp`: `pip install yt-dlp`
   - 检查网络连接和代理设置
   - 查看日志文件获取详细错误信息

3. **依赖问题**
   - 运行 `pip install -e .` 重新安装依赖
   - 确认Python版本 >= 3.9
   - 如果缺少可选依赖，程序会使用备用方案

### 日志查看

```bash
# 查看完整日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log
```

## 开发和贡献

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest test/ -v
```

### 代码格式化

```bash
# 使用ruff格式化
ruff check --fix src/
ruff format src/
```

### 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 注意事项

### 版权和合规
- 本工具仅供学习和交流使用
- 请遵守YouTube和B站的服务条款
- 尊重原创者版权，标注视频来源
- 建议获得原作者许可后再进行转载

### 使用建议
- 合理控制下载和上传频率
- 做好内容审核，确保内容质量
- 定期更新认证信息
- 监控日志文件，及时处理异常

### 技术限制
- 依赖网络环境，可能需要代理
- 视频处理需要足够存储空间
- 大文件下载可能耗时较长
- API限制可能影响功能稳定性

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 免责声明

本工具仅供学习和研究使用。使用者需要自行承担使用本工具的法律责任，包括但不限于版权侵权、违反平台服务条款等风险。开发者不对使用本工具产生的任何后果承担责任。

---

**⚠️ 重要提醒**: 请务必遵守相关法律法规和平台规则，尊重知识产权，合理使用本工具。
