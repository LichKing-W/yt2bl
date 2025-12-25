#!/bin/bash

# YouTube to Bilibili 项目安装脚本

echo "🚀 YouTube to Bilibili 项目安装脚本"
echo "=================================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 需要Python 3.9或更高版本，当前版本: $python_version"
    exit 1
fi

echo "✅ Python版本检查通过: $python_version"

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source .venv/bin/activate

# 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📥 安装依赖包..."
pip install -e .

# 创建配置文件
if [ ! -f ".env" ]; then
    echo "⚙️ 创建配置文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 配置文件，请根据需要修改配置"
fi

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p data logs config

# 测试安装
echo "🧪 测试安装..."
python -c "
try:
    from src.main import YouTubeToBilibili
    print('✅ 安装成功！')
except Exception as e:
    print(f'❌ 安装测试失败: {e}')
"

echo ""
echo "🎉 安装完成！"
echo ""
echo "使用方法:"
echo "  1. 激活虚拟环境: source .venv/bin/activate"
echo "  2. 运行程序: python -m src.main"
echo "  3. 或使用命令: yt2bl"
echo ""
echo "配置说明:"
echo "  - 编辑 .env 文件配置YouTube API密钥和B站认证信息"
echo "  - 下载的视频将保存在 data/ 目录"
echo "  - 日志文件保存在 logs/ 目录"
echo ""
echo "注意事项:"
echo "  - 首次运行将使用模拟数据"
echo "  - 要启用真实下载，需要安装 yt-dlp: pip install yt-dlp"
echo "  - 要启用YouTube API搜索，需要配置API密钥"
