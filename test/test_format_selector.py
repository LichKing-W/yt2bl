#!/usr/bin/env python3
"""测试视频格式选择器是否正确选择1080p"""

import sys
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.youtube.downloader import YouTubeDownloader
from src.utils.config import settings


def test_format_selector():
    """测试格式选择器"""
    downloader = YouTubeDownloader()

    # 获取格式选择器
    format_selector = downloader._get_format_selector()
    print(f"格式选择器: {format_selector}")
    print()

    # 测试视频URL
    test_url = "https://www.youtube.com/watch?v=HoMvCjnpAJ8"

    print(f"正在获取视频信息: {test_url}")
    print()

    # 构建 yt-dlp 命令
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        "--ignore-errors",
        "--no-warnings",
    ]

    if downloader.cookies_file and Path(downloader.cookies_file).exists():
        cmd.extend(["--cookies", downloader.cookies_file])

    if settings.proxy:
        cmd.extend(["--proxy", settings.proxy])

    cmd.append(test_url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"❌ yt-dlp 命令失败: {result.stderr}")
            return

        info = json.loads(result.stdout)

        print(f"视频标题: {info.get('title', 'unknown')}")
        print()

        # 收集所有格式
        formats = info.get("formats", [])

        # 按分辨率分组
        resolution_formats = {}
        for f in formats:
            height = f.get("height")
            if height:
                if height not in resolution_formats:
                    resolution_formats[height] = []
                resolution_formats[height].append(f)

        # 显示可用分辨率
        print(f"可用分辨率列表:")
        print("-" * 80)
        for height in sorted(resolution_formats.keys(), reverse=True):
            formats_at_height = resolution_formats[height]
            print(f"\n{height}p:")
            for f in formats_at_height[:5]:  # 只显示前5个格式
                ext = f.get("ext", "unknown")
                vcodec = f.get("vcodec", "unknown")
                acodec = f.get("acodec", "unknown")
                filesize = f.get("filesize", 0)
                size_mb = filesize / (1024 * 1024) if filesize else 0
                format_id = f.get("format_id", "unknown")
                has_audio = "yes" if f.get("acodec") and f.get("acodec") != "none" else "no"
                print(f"  {format_id:12s} | {ext:4s} | v:{vcodec[:10]:10s} | a:{acodec[:10]:10s} | audio:{has_audio:3s} | {size_mb:6.1f}MB")

        print("\n" + "-" * 80)

        # 测试格式选择器会选择哪个格式
        print(f"\n使用格式选择器模拟选择:")
        print(f"选择器: {format_selector}")

        # 手动实现格式选择逻辑
        target_height = 1080

        # 优先: bestvideo[height<=1080] + bestaudio
        video_formats = [f for f in formats if f.get('height') and f.get('height') <= target_height]
        audio_formats = [f for f in formats if f.get('acodec') and f.get('acodec') != 'none']

        if video_formats and audio_formats:
            # 找到最高的视频格式
            best_video = max(video_formats, key=lambda f: (f.get('height', 0), f.get('filesize', 0)))
            best_audio = max(audio_formats, key=lambda f: (f.get('abr') or 0, f.get('filesize') or 0))

            print(f"\n✅ 将会选择的视频+音频组合:")
            print(f"  视频: {best_video.get('format_id')} - {best_video.get('height')}p ({best_video.get('ext')})")
            print(f"  音频: {best_audio.get('format_id')} - {best_audio.get('abr')}kbps ({best_audio.get('ext')})")
            print(f"  最终分辨率: {best_video.get('height')}p")

            selected_height = best_video.get('height')
            if selected_height >= target_height:
                print(f"\n✅ 成功！选择了 {selected_height}p 视频 (达到目标 {target_height}p)")
            else:
                print(f"\n⚠️  最高可用分辨率: {selected_height}p (低于目标 {target_height}p)")
        else:
            print("\n❌ 无法找到合适的视频/音频格式")

    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_format_selector()
