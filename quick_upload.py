#!/usr/bin/env python3
"""
快速B站上传脚本
简化版本，用于快速上传data目录中的视频
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import logger
from src.utils.config import settings
from src.bilibili.uploader import BilibiliUploader
from src.bilibili.models import BilibiliVideo


async def quick_upload(video_path: str, title: str = None, description: str = None):
    """快速上传视频到B站"""

    video_file = Path(video_path)
    if not video_file.exists():
        print(f"❌ 视频文件不存在: {video_path}")
        return False

    # 检查配置
    if not all([settings.bilibili_sessdata, settings.bilibili_bili_jct, settings.bilibili_dedeuser_id]):
        print("❌ 缺少B站认证信息，请检查.env配置")
        return False

    # 创建上传器
    uploader = BilibiliUploader()

    # 检查登录状态
    print("🔐 检查登录状态...")
    login_ok = await uploader.check_login_status()
    if not login_ok:
        print("❌ B站登录状态验证失败")
        return False

    print("✅ 登录状态正常")

    # 准备视频信息
    if not title:
        title = video_file.stem.replace("_", " ")

    if not description:
        description = f"""
📚 精彩的技术分享视频

🎯 学习要点：
• 实用的技术讲解
• 清晰的步骤演示
• 详细的代码示例

⚠️ 免责声明：
本视频为转载内容，版权归原作者所有，仅用于学习和交流目的。

🔔 如果这个视频对你有帮助，别忘了点赞、收藏和关注哦！
        """.strip()

    # 创建B站视频对象
    bilibili_video = BilibiliVideo(
        title=title,
        description=description,
        tags=["编程", "教程", "技术", "学习", "分享"],
        category_id=122,  # 知识区
        video_path=str(video_file),
        copyright=2,  # 转载
        source="来源：YouTube",
        tid=122,
    )

    print(f"📤 开始上传: {title}")
    print(f"📁 文件: {video_file.name}")
    print(f"📊 大小: {video_file.stat().st_size / (1024 * 1024):.1f}MB")

    # 上传视频
    try:
        result = await uploader.upload_video(bilibili_video)

        if result.success:
            print("✅ 上传成功！")
            if result.bvid:
                print(f"🔗 视频链接: {result.video_url}")
            print(f"⏱️ 上传耗时: {result.upload_duration:.1f}秒")
            return True
        else:
            print(f"❌ 上传失败: {result.message}")
            return False

    except Exception as e:
        print(f"❌ 上传异常: {str(e)}")
        logger.error(f"上传异常: {str(e)}")
        return False


async def upload_all_videos():
    """上传data目录中的所有视频"""
    data_dir = Path(settings.download_path)

    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return

    # 获取视频文件
    video_extensions = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    video_files = []

    for file_path in data_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            video_files.append(file_path)

    if not video_files:
        print("❌ data目录中没有找到视频文件")
        return

    print(f"📹 找到 {len(video_files)} 个视频文件")

    success_count = 0
    for i, video_path in enumerate(video_files, 1):
        print(f"\n🎬 处理视频 {i}/{len(video_files)}: {video_path.name}")

        success = await quick_upload(str(video_path))
        if success:
            success_count += 1

        # 上传间隔（避免频率限制）
        if i < len(video_files):
            print("⏳ 等待上传间隔...")
            await asyncio.sleep(10)  # 10秒间隔

    print(f"\n🎊 批量上传完成！成功: {success_count}/{len(video_files)}")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="快速B站视频上传工具")
    parser.add_argument("--file", type=str, help="指定要上传的视频文件路径")
    parser.add_argument("--title", type=str, help="视频标题")
    parser.add_argument("--description", type=str, help="视频描述")
    parser.add_argument("--all", action="store_true", help="上传data目录中的所有视频")

    args = parser.parse_args()

    if args.file:
        # 上传指定文件
        await quick_upload(args.file, args.title, args.description)
    elif args.all:
        # 上传所有文件
        await upload_all_videos()
    else:
        # 交互式选择
        data_dir = Path(settings.download_path)
        video_files = []

        if data_dir.exists():
            video_extensions = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
            for file_path in data_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    video_files.append(file_path)

        if not video_files:
            print("❌ data目录中没有找到视频文件")
            return

        print("📹 可上传的视频文件:")
        for i, video_path in enumerate(video_files, 1):
            size_mb = video_path.stat().st_size / (1024 * 1024)
            print(f"  {i}. {video_path.name} ({size_mb:.1f}MB)")

        try:
            choice = input(f"\n请选择要上传的视频 (1-{len(video_files)}) 或 'all' 上传全部: ").strip()

            if choice.lower() == "all":
                await upload_all_videos()
            else:
                idx = int(choice) - 1
                if 0 <= idx < len(video_files):
                    await quick_upload(str(video_files[idx]))
                else:
                    print("❌ 无效的选择")

        except (ValueError, KeyboardInterrupt):
            print("取消操作")


if __name__ == "__main__":
    asyncio.run(main())
