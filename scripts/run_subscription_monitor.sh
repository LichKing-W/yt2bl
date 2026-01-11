#!/bin/bash
# YouTube订阅监控脚本
# 定期检查YouTuber的新视频，自动下载并上传到B站
# 推荐使用 crontab 定时运行

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}YouTube订阅监控器${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}警告: 未检测到虚拟环境${NC}"
    echo "建议先激活虚拟环境: source .venv/bin/activate"
    echo ""
fi

# 检查必需的配置
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到.env文件${NC}"
    echo "请先复制.env.example到.env并填写配置"
    exit 1
fi

# 检查YouTuber列表
if [ ! -f "youtuber.txt" ]; then
    echo -e "${RED}错误: 未找到youtuber.txt文件${NC}"
    echo "请创建youtuber.txt并添加要监控的YouTuber"
    exit 1
fi

# 检查B站登录配置
source .env
if [ -z "$BILIBILI_SESSDATA" ]; then
    echo -e "${RED}错误: BILIBILI_SESSDATA未配置${NC}"
    echo "上传到B站需要登录信息"
    exit 1
fi

# 运行监控
echo -e "${GREEN}开始检查新视频...${NC}"
echo ""

python -m src.subscription_monitor "$@"
