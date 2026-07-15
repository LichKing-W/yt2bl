"""测试字幕合并算法改进"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.subtitle_processor import SubtitleProcessor


def test_word_count():
    """测试单词计数"""
    print("\n=== 测试单词计数 ===")

    processor = SubtitleProcessor()

    # 测试短文本
    text1 = "Hello world"
    count1 = processor._count_words(text1)
    print(f"短文本 ('{text1}'): {count1} 个单词")
    assert count1 == 2, f"短文本计数失败: {count1} != 2"

    # 测试较长文本
    text2 = "This is a test with multiple words"
    count2 = processor._count_words(text2)
    print(f"较长文本: {count2} 个单词")
    assert count2 == 7, f"较长文本计数失败: {count2} != 7"

    # 测试带标点符号的文本
    text3 = "Hello, world! How are you"
    count3 = processor._count_words(text3)
    print(f"带标点符号的文本: {count3} 个单词")
    assert count3 == 5, f"带标点符号文本计数失败: {count3} != 5"

    # 测试纯中文（会被识别为"单词"）
    text4 = "这是一段很长的中文文本用于测试计数功能是否正常工作"
    count4 = processor._count_words(text4)
    print(f"纯中文: {count4} 个单词（中文字符序列）")
    # Note: Regex treats Chinese characters as word chars, so the entire line counts as 1
    assert count4 >= 1, f"纯中文计数失败: {count4}"

    print("✅ 单词计数测试通过!")


def test_merge_with_long_text():
    """测试包含长文本的合并（超过15个单词不合并）"""
    print("\n=== 测试长文本合并逻辑 ===")

    processor = SubtitleProcessor()

    # 创建测试字幕：包含超过15个单词的行
    test_subtitles = [
        {
            "index": 1,
            "start": "00:00:01,000",
            "end": "00:00:04,000",
            "text": "This is a very long line with many words that should exceed fifteen words"
        },
        {
            "index": 2,
            "start": "00:00:04,500",
            "end": "00:00:08,000",
            "text": "Short text"
        },
        {
            "index": 3,
            "start": "00:00:08,500",
            "end": "00:00:12,000",
            "text": "Another short text"
        },
        {
            "index": 4,
            "start": "00:00:12,500",
            "end": "00:00:16,000",
            "text": "Third line"
        },
        {
            "index": 5,
            "start": "00:00:16,500",
            "end": "00:00:20,000",
            "text": "Fourth line"
        },
    ]

    # 创建测试文件
    test_file = Path("/tmp/test_merge_long.srt")
    lines = []
    for sub in test_subtitles:
        lines.append(str(sub["index"]))
        lines.append(f"{sub['start']} --> {sub['end']}")
        lines.append(sub["text"])
        lines.append("")
    test_file.write_text("\n".join(lines), encoding="utf-8")

    # 执行合并
    result_file = processor.merge_subtitle_lines(test_file)

    # 读取并验证结果
    merged_subs = processor._parse_srt_file(result_file)

    print(f"\n原始字幕: {len(test_subtitles)} 条")
    print(f"合并后: {len(merged_subs)} 条")

    for i, sub in enumerate(merged_subs):
        word_count = processor._count_words(sub['text'])
        print(f"  {i+1}. [{word_count} 单词] {sub['text']}")

    # 验证：
    # 第1行应该独立（超过15个单词）
    # 第2-3行应该合并
    # 第4-5行应该合并
    assert len(merged_subs) == 3, f"应该合并为3条，实际{len(merged_subs)}条"

    # 验证第一条
    assert "This is a very long line" in merged_subs[0]["text"]
    assert merged_subs[0]["text"] == test_subtitles[0]["text"]

    # 验证第二条（2和3合并）
    assert "Short text" in merged_subs[1]["text"]
    assert "Another short text" in merged_subs[1]["text"]

    # 验证第三条（4和5合并）
    assert "Third line" in merged_subs[2]["text"]
    assert "Fourth line" in merged_subs[2]["text"]

    # 清理
    test_file.unlink()
    if result_file.exists():
        result_file.unlink()

    print("✅ 长文本合并测试通过!")


def test_merge_with_short_text():
    """测试包含短文本的合并（15个单词以内正常合并）"""
    print("\n=== 测试短文本合并逻辑 ===")

    processor = SubtitleProcessor()

    # 创建测试字幕：所有合并后都不超过15个单词
    test_subtitles = [
        {
            "index": 1,
            "start": "00:00:01,000",
            "end": "00:00:04,000",
            "text": "First line here"
        },
        {
            "index": 2,
            "start": "00:00:04,500",
            "end": "00:00:08,000",
            "text": "Second line text"
        },
        {
            "index": 3,
            "start": "00:00:08,500",
            "end": "00:00:12,000",
            "text": "Third line is here"
        },
        {
            "index": 4,
            "start": "00:00:12,500",
            "end": "00:00:16,000",
            "text": "Fourth line"
        },
    ]

    # 创建测试文件
    test_file = Path("/tmp/test_merge_short.srt")
    lines = []
    for sub in test_subtitles:
        lines.append(str(sub["index"]))
        lines.append(f"{sub['start']} --> {sub['end']}")
        lines.append(sub["text"])
        lines.append("")
    test_file.write_text("\n".join(lines), encoding="utf-8")

    # 执行合并
    result_file = processor.merge_subtitle_lines(test_file)

    # 读取并验证结果
    merged_subs = processor._parse_srt_file(result_file)

    print(f"\n原始字幕: {len(test_subtitles)} 条")
    print(f"合并后: {len(merged_subs)} 条")

    for i, sub in enumerate(merged_subs):
        word_count = processor._count_words(sub['text'])
        print(f"  {i+1}. [{word_count} 单词] {sub['text']}")

    # 验证：应该正常两两合并
    assert len(merged_subs) == 2, f"应该合并为2条，实际{len(merged_subs)}条"

    # 验证第一条（1和2合并）
    assert "First line here" in merged_subs[0]["text"]
    assert "Second line text" in merged_subs[0]["text"]

    # 验证第二条（3和4合并）
    assert "Third line is here" in merged_subs[1]["text"]
    assert "Fourth line" in merged_subs[1]["text"]

    # 清理
    test_file.unlink()
    if result_file.exists():
        result_file.unlink()

    print("✅ 短文本合并测试通过!")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("字幕合并算法改进测试")
    print("=" * 60)

    try:
        test_word_count()
        test_merge_with_long_text()
        test_merge_with_short_text()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
