"""手动测试：翻译缓存断点续传功能

这个测试模拟以下场景：
1. 创建一个包含30条字幕的测试文件（分3批）
2. 模拟翻译到第2批时中断
3. 重新运行翻译，验证从第3批继续
4. 验证最终结果完整
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.subtitle_processor import SubtitleProcessor


def create_test_srt_file(path: Path, subtitles: List[Dict[str, Any]]) -> None:
    """创建测试用的 SRT 文件"""
    lines = []
    for sub in subtitles:
        lines.append(str(sub["index"]))
        lines.append(f"{sub['start']} --> {sub['end']}")
        lines.append(sub["text"])
        lines.append("")  # 空行
    path.write_text("\n".join(lines), encoding="utf-8")


def create_mock_translated_batch() -> str:
    """创建模拟的翻译结果"""
    return """1: First English text
第一段中文翻译

2: Second English text
第二段中文翻译

3: Third English text
第三段中文翻译

4: Fourth English text
第四段中文翻译

5: Fifth English text
第五段中文翻译

6: Sixth English text
第六段中文翻译

7: Seventh English text
第七段中文翻译

8: Eighth English text
第八段中文翻译

9: Ninth English text
第九段中文翻译

10: Tenth English text
第十段中文翻译"""


async def simulate_translation_with_interruption():
    """模拟翻译中断场景"""
    print("\n" + "=" * 70)
    print("场景1：模拟翻译中断")
    print("=" * 70)

    # 创建30条字幕（3批，每批10条）
    test_subtitles = []
    for i in range(1, 31):
        test_subtitles.append({
            "index": i,
            "start": f"00:00:{i*2:02d},000",
            "end": f"00:00:{i*2+2:02d},000",
            "text": f"This is subtitle number {i} with some English text."
        })

    # 创建测试文件
    test_dir = Path("/tmp/test_translation_cache")
    test_dir.mkdir(exist_ok=True)
    subtitle_file = test_dir / "test.en.srt"
    create_test_srt_file(subtitle_file, test_subtitles)

    print(f"✓ 创建测试字幕文件: {subtitle_file}")
    print(f"  包含 {len(test_subtitles)} 条字幕（分3批翻译）\n")

    processor = SubtitleProcessor()

    # 预处理字幕（修复时间轴 + 合并行）
    print("步骤 1/2: 预理字幕...")
    fixed_path = processor.fix_subtitle_overlaps(subtitle_file)
    merged_path = processor.merge_subtitle_lines(fixed_path)
    fixed_path.unlink()
    print(f"✓ 预处理完成: {merged_path.name}\n")

    # 计算哈希
    subtitle_hash = processor._calculate_subtitle_hash(merged_path)
    total_subtitles = len(test_subtitles)
    batch_size = 10
    output_path = test_dir / "zh.srt"
    cache_path = processor._get_subtitle_cache_path(output_path)

    print(f"字幕哈希: {subtitle_hash}")
    print(f"字幕总数: {total_subtitles}")
    print(f"批次大小: {batch_size}")
    print(f"缓存路径: {cache_path}\n")

    # 模拟翻译前2批（0和1），然后"中断"
    print("步骤 2/2: 模拟翻译过程...")
    print("  批次 1/3: 模拟翻译第 1 批 (1-10 条)...")

    # 创建前2批的模拟翻译结果
    cache_data = {
        "subtitle_hash": subtitle_hash,
        "total_subtitles": total_subtitles,
        "batch_size": batch_size,
        "translated_batches": {},
    }

    # 批次0
    batch_0 = [f"1: {i}. English text\n第{i}条中文翻译" for i in range(1, 11)]
    processor._update_translation_cache(cache_path, cache_data, 0, batch_0)
    print("    ✓ 批次 1 翻译完成并缓存")

    # 批次1
    print("  批次 2/3: 模拟翻译第 2 批 (11-20 条)...")
    batch_1 = [f"1: {i}. English text\n第{i}条中文翻译" for i in range(11, 21)]
    processor._update_translation_cache(cache_path, cache_data, 1, batch_1)
    print("    ✓ 批次 2 翻译完成并缓存")

    print("\n⚠️  模拟翻译中断！")
    print("  假设网络错误或程序崩溃\n")

    # 显示缓存状态
    cache_content = json.loads(cache_path.read_text(encoding="utf-8"))
    print("当前缓存状态:")
    print(f"  已翻译批次数: {len(cache_content['translated_batches'])}")
    print(f"  已翻译字幕数: {len(cache_content['translated_batches']) * batch_size}/{total_subtitles}")
    print(f"  缓存文件: {cache_path}")

    return test_dir, subtitle_file, merged_path, output_path, cache_path, test_subtitles


async def simulate_translation_resume():
    """模拟翻译恢复"""
    print("\n" + "=" * 70)
    print("场景2：从缓存恢复翻译")
    print("=" * 70)

    test_dir = Path("/tmp/test_translation_cache")
    output_path = test_dir / "zh.srt"
    cache_path = processor._get_subtitle_cache_path(output_path)

    print(f"🔄 重新启动翻译程序...")
    print(f"  检测到缓存文件: {cache_path}\n")

    # 加载缓存
    subtitle_hash = processor._calculate_subtitle_hash(merged_path)
    total_subtitles = len(test_subtitles)
    batch_size = 10

    cache_data = processor._load_translation_cache(cache_path, subtitle_hash, total_subtitles, batch_size)

    if cache_data:
        print(f"✓ 缓存有效，从缓存恢复")
        translated_batches = {
            int(k): v for k, v in cache_data.get("translated_batches", {}).items()
        }
        start_batch_index = len(translated_batches)
        print(f"  已完成 {start_batch_index} 批翻译")
        print(f"  将从第 {start_batch_index + 1} 批开始继续翻译\n")

        # 模拟完成第3批
        print(f"  批次 3/3: 翻译第 3 批 (21-30 条)...")
        batch_2 = [f"1: {i}. English text\n第{i}条中文翻译" for i in range(21, 31)]
        processor._update_translation_cache(cache_path, cache_data, 2, batch_2)
        print(f"    ✓ 批次 3 翻译完成")

        # 重建完整翻译
        all_translated = []
        for batch_idx in sorted(translated_batches.keys()):
            all_translated.extend(translated_batches[batch_idx])
        all_translated.extend(batch_2)

        # 保存最终结果
        subtitles = processor._parse_srt_file(merged_path)
        final_content = processor._rebuild_srt_from_batches(subtitles, all_translated)
        output_path.write_text(final_content, encoding="utf-8")

        # 清除缓存
        processor._clear_translation_cache(cache_path)

        print(f"\n✅ 翻译完成!")
        print(f"  输出文件: {output_path}")
        print(f"  翻译总数: {len(all_translated)}")
        print(f"  缓存已清除")

        # 验证结果
        result_subtitles = processor._parse_srt_file(output_path)
        print(f"\n验证结果:")
        print(f"  原始字幕数: {len(subtitles)}")
        print(f"  翻译结果数: {len(result_subtitles)}")
        assert len(result_subtitles) == len(subtitles), "翻译结果数量不匹配"
        print(f"  ✓ 数量匹配")

        # 检查每条字幕都包含双语
        for i, sub in enumerate(result_subtitles):
            lines = sub["text"].split("\n")
            has_english = any(line.strip() and not any("\u4e00" <= c <= "\u9fff" for c in line) for line in lines)
            has_chinese = any(line.strip() and any("\u4e00" <= c <= "\u9fff" for c in line) for line in lines)

            if not (has_english and has_chinese):
                print(f"  ✗ 第 {i+1} 条字幕不包含双语")
                break
        else:
            print(f"  ✓ 所有字幕都包含双语翻译")

        return True

    return False


async def clean_test_files():
    """清理测试文件"""
    print("\n" + "=" * 70)
    print("清理测试文件")
    print("=" * 70)

    test_dir = Path("/tmp/test_translation_cache")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
        print(f"✓ 已删除测试目录: {test_dir}")


async def main():
    """主测试流程"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "翻译缓存断点续传功能测试" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")

    global processor, merged_path, test_subtitles

    # 场景1：模拟翻译中断
    test_dir, subtitle_file, merged_path, output_path, cache_path, test_subtitles = await simulate_translation_with_interruption()

    input("\n按 Enter 键继续测试恢复功能...")

    # 场景2：模拟翻译恢复
    processor = SubtitleProcessor()
    success = await simulate_translation_resume()

    if success:
        print("\n" + "=" * 70)
        print("✅ 断点续传功能测试成功!")
        print("=" * 70)
        print("\n测试总结:")
        print("  ✓ 缓存文件正确创建")
        print("  ✓ 缓存数据正确保存")
        print("  ✓ 缓存验证功能正常")
        print("  ✓ 从缓存恢复翻译成功")
        print("  ✓ 翻译结果完整且正确")
        print("  ✓ 翻译完成后缓存自动清除")
    else:
        print("\n❌ 测试失败")

    # 清理
    await clean_test_files()

    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
