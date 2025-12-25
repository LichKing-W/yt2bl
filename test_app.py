#!/usr/bin/env python3
"""简单的应用测试脚本"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import YouTubeToBilibili


async def test_search():
    """测试搜索功能"""
    print("🧪 测试搜索功能...")
    
    app = YouTubeToBilibili()
    videos = await app.searcher.search_trending_cs_videos(3)
    
    print(f"✅ 搜索到 {len(videos)} 个视频")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video.title} (ID: {video.video_id})")
    
    return videos


async def test_download():
    """测试下载功能"""
    print("\n🧪 测试下载功能...")
    
    app = YouTubeToBilibili()
    videos = await app.searcher.search_trending_cs_videos(1)
    
    if videos:
        video = videos[0]
        print(f"下载视频: {video.title}")
        
        downloaded_path = await app.downloader.download_video(video)
        
        if downloaded_path:
            print(f"✅ 下载成功: {downloaded_path}")
            return True
        else:
            print("❌ 下载失败")
            return False
    else:
        print("❌ 没有视频可下载")
        return False


async def main():
    """主测试函数"""
    print("🚀 YouTube to Bilibili 应用测试")
    print("=" * 40)
    
    try:
        # 测试搜索
        videos = await test_search()
        
        # 测试下载
        success = await test_download()
        
        print("\n📊 测试结果:")
        print(f"搜索功能: {'✅ 通过' if videos else '❌ 失败'}")
        print(f"下载功能: {'✅ 通过' if success else '❌ 失败'}")
        
        if videos and success:
            print("\n🎉 所有测试通过！应用运行正常。")
        else:
            print("\n⚠️ 部分测试失败，请检查配置。")
    
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
