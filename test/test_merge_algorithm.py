"""测试字幕合并算法改进"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.subtitle_processor import SubtitleProcessor


def test_chinese_character_count():
    """测试中文字符计数"""
    print("\n=== 测试中文字符计数 ===")

    processor = SubtitleProcessor()

    # 测试纯中文
    text1 = "这是一段很长的中文文本用于测试计数功能是否正常工作"
    count1 = processor._count_chinese_characters(text1)
    print(f"纯中文 ({len(text1)} 字符): {count1} 个中文字符")
    assert count1 == len(text1), f"纯中文计数失败: {count1} != {len(text1)}"

    # 测试混合文本
    text2 = "Hello 世界！This is a test 测试"
    count2 = processor._count_chinese_characters(text2)
    print(f"混合文本: {count2} 个中文字符")
    assert count2 == 4, f"混合文本计数失败: {count2} != 4"

    # 测试纯英文
    text3 = "This is English only text"
    count3 = processor._count_chinese_characters(text3)
    print(f"纯英文: {count3} 个中文字符")
    assert count3 == 0, f"纯英文计数失败: {count3} != 0"

    print("✅ 中文字符计数测试通过!")


def test_merge_with_long_chinese():
    """测试包含长中文文本的合并"""
    print("\n=== 测试长中文文本合并逻辑 ===")

    processor = SubtitleProcessor()

    # 创建测试字幕：包含超过20个中文字符的行
    test_subtitles = [
        {
            "index": 1,
            "start": "00:00:01,000",
            "end": "00:00:04,000",
            "text": "这是一段非常长的中文文本超过了二十个字符应该独立显示"
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
            "text": "第三行短文本"
        },
        {
            "index": 5,
            "start": "00:00:16,500",
            "end": "00:00:20,000",
            "text": "第四行短文本"
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
        zh_count = processor._count_chinese_characters(sub['text'])
        print(f"  {i+1}. [{zh_count} 中文字符] {sub['text']}")

    # 验证：
    # 第1行应该独立（超过20个中文字符）
    # 第2-3行应该合并
    # 第4-5行应该合并
    assert len(merged_subs) == 3, f"应该合并为3条，实际{len(merged_subs)}条"

    # 验证第一条
    assert "这是一段非常长的中文文本" in merged_subs[0]["text"]
    assert merged_subs[0]["text"] == test_subtitles[0]["text"]

    # 验证第二条（2和3合并）
    assert "Short text" in merged_subs[1]["text"]
    assert "Another short text" in merged_subs[1]["text"]

    # 验证第三条（4和5合并）
    assert "第三行短文本" in merged_subs[2]["text"]
    assert "第四行短文本" in merged_subs[2]["text"]

    # 清理
    test_file.unlink()
    if result_file.exists():
        result_file.unlink()

    print("✅ 长中文文本合并测试通过!")


def test_merge_with_short_chinese():
    """测试包含短中文文本的合并"""
    print("\n=== 测试短中文文本合并逻辑 ===")

    processor = SubtitleProcessor()

    # 创建测试字幕：所有行都不超过20个中文字符
    test_subtitles = [
        {
            "index": 1,
            "start": "00:00:01,000",
            "end": "00:00:04,000",
            "text": "第一行文本"
        },
        {
            "index": 2,
            "start": "00:00:04,500",
            "end": "00:00:08,000",
            "text": "第二行文本"
        },
        {
            "index": 3,
            "start": "00:00:08,500",
            "end": "00:00:12,000",
            "text": "Third line"
        },
        {
            "index": 4,
            "start": "00:00:12,500",
            "end": "00:00:16,000",
            "text": "第四行"
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
        print(f"  {i+1}. {sub['text']}")

    # 验证：应该正常两两合并
    assert len(merged_subs) == 2, f"应该合并为2条，实际{len(merged_subs)}条"

    # 验证第一条（1和2合并）
    assert "第一行文本" in merged_subs[0]["text"]
    assert "第二行文本" in merged_subs[0]["text"]

    # 验证第二条（3和4合并）
    assert "Third line" in merged_subs[1]["text"]
    assert "第四行" in merged_subs[1]["text"]

    # 清理
    test_file.unlink()
    if result_file.exists():
        result_file.unlink()

    print("✅ 短中文文本合并测试通过!")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("字幕合并算法改进测试")
    print("=" * 60)

    try:
        test_chinese_character_count()
        test_merge_with_long_chinese()
        test_merge_with_short_chinese()

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
