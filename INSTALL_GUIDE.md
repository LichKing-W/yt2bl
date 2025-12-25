# 安装指南

## 问题诊断

由于网络限制，`uv sync` 和 `pip install` 可能会遇到连接问题。以下是解决方案：

## 方法1：开发环境运行（推荐）

项目已经配置好了开发环境，可以直接运行：

```bash
# 使用开发脚本
./scripts/run_dev.sh

# 或者手动设置环境变量运行
export PYTHONPATH="/home/keith/youtube-projects:$PYTHONPATH"
python -c "import sys; sys.path.insert(0, '/home/keith/youtube-projects'); from src.main import cli; cli()"
```

## 方法2：手动安装依赖

如果需要完整的依赖环境，可以逐个安装核心包：

```bash
# 核心依赖（优先级从高到低）
pip install requests
pip install beautifulsoup4
pip install pydantic
pip install rich
pip install yt-dlp

# 可选依赖
pip install moviepy          # 视频处理
pip install bilibili-api-python # B站API
```

## 方法3：使用离线包

如果网络完全受限，可以：

1. 在有网络的环境下载wheel文件
2. 传输到目标环境进行离线安装
3. 或使用conda环境（如果可用）

## 项目已测试功能

✅ 配置管理模块正常工作
✅ 日志系统正常运行  
✅ YouTube视频模型功能正常
✅ 核心类可以正常导入
✅ CS相关性检测正常
✅ 质量评分功能正常

## 使用说明

1. 复制环境变量文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件添加必要的配置（如B站认证信息）

3. 运行程序：
```bash
./scripts/run_dev.sh
```

## 注意事项

- 程序在无网络环境下可以测试核心功能
- 下载和上传功能需要网络连接
- 视频处理需要安装FFmpeg
- 建议在有网络环境下安装完整依赖
