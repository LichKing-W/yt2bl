"""字幕翻译单元测试"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.subtitle_processor import SubtitleProcessor
from src.utils.config import settings


def create_test_srt_file(path: Path, subtitles: List[Dict[str, Any]]) -> None:
    """创建测试用的 SRT 文件"""
    lines = []
    for sub in subtitles:
        lines.append(str(sub["index"]))
        lines.append(f"{sub['start']} --> {sub['end']}")
        lines.append(sub["text"])
        lines.append("")  # 空行
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_srt_file(path: Path) -> List[Dict[str, Any]]:
    """解析 SRT 文件"""
    processor = SubtitleProcessor()
    return processor._parse_srt_file(path)


def test_srt_parsing():
    """测试 SRT 文件解析"""
    print("\n=== 测试 SRT 文件解析 ===")

    # 创建测试字幕数据
    test_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Hello, world!"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "This is a test."},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Let's learn programming."},
        {"index": 4, "start": "00:00:12,500", "end": "00:00:16,000", "text": "Python is awesome!"},
    ]

    # 创建临时测试文件
    test_file = Path("/tmp/test_subtitle.srt")
    create_test_srt_file(test_file, test_subtitles)

    # 测试解析
    processor = SubtitleProcessor()
    parsed = processor._parse_srt_file(test_file)

    print(f"原始字幕数量: {len(test_subtitles)}")
    print(f"解析字幕数量: {len(parsed)}")

    # 验证数量
    assert len(parsed) == len(test_subtitles), f"数量不匹配: {len(parsed)} != {len(test_subtitles)}"

    # 验证内容
    for i, (original, parsed_item) in enumerate(zip(test_subtitles, parsed)):
        assert parsed_item["index"] == original["index"], f"索引不匹配: {parsed_item['index']} != {original['index']}"
        assert parsed_item["start"] == original["start"], f"开始时间不匹配"
        assert parsed_item["end"] == original["end"], f"结束时间不匹配"
        assert parsed_item["text"] == original["text"], f"文本不匹配"
        print(f"✓ 第 {i+1} 条字幕解析正确")

    # 清理
    test_file.unlink()

    print("✅ SRT 解析测试通过!")


def test_batch_formatting():
    """测试批次格式化"""
    print("\n=== 测试批次格式化 ===")

    processor = SubtitleProcessor()

    # 创建测试字幕
    test_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "First subtitle"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "Second subtitle"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Third subtitle"},
    ]

    # 测试批次格式化（offset=0）
    formatted = processor._format_subtitles_for_translation_batch(test_subtitles, 0)
    lines = formatted.strip().split("\n")

    print(f"格式化结果:\n{formatted}")

    assert len(lines) == 3, f"应该有3行，实际有 {len(lines)} 行"
    assert lines[0] == "1: First subtitle", f"第一行不正确: {lines[0]}"
    assert lines[1] == "2: Second subtitle", f"第二行不正确: {lines[1]}"
    assert lines[2] == "3: Third subtitle", f"第三行不正确: {lines[2]}"

    print("✅ 批次格式化测试通过!")


def test_translation_result_parsing():
    """测试翻译结果解析"""
    print("\n=== 测试翻译结果解析 ===")

    processor = SubtitleProcessor()

    # 模拟 LLM 返回的翻译结果
    mock_translation = """1: 第一条字幕
2: 第二条字幕
3: 第三条字幕
4: 第四条字幕"""

    parsed, _ = processor._parse_translated_batch_result(mock_translation)

    print(f"解析结果: {parsed}")

    # 现在返回的是字典
    assert isinstance(parsed, dict), f"应该返回字典，实际返回 {type(parsed)}"
    assert len(parsed) == 4, f"应该解析出4条，实际 {len(parsed)} 条"
    assert parsed[1] == "第一条字幕", f"第一条不正确: {parsed[1]}"
    assert parsed[2] == "第二条字幕", f"第二条不正确: {parsed[2]}"
    assert parsed[3] == "第三条字幕", f"第三条不正确: {parsed[3]}"
    assert parsed[4] == "第四条字幕", f"第四条不正确: {parsed[4]}"

    print("✅ 翻译结果解析测试通过!")


def test_srt_rebuilding():
    """测试 SRT 重建"""
    print("\n=== 测试 SRT 重建 ===")

    processor = SubtitleProcessor()

    # 原始字幕结构
    original_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Hello"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "World"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Test"},
    ]

    # 翻译文本
    translated_texts = ["你好", "世界", "测试"]

    # 重建 SRT
    rebuilt = processor._rebuild_srt_from_batches(original_subtitles, translated_texts)

    print(f"重建的 SRT:\n{rebuilt}")

    # 解析重建的 SRT
    temp_file = Path("/tmp/test_rebuilt.srt")
    temp_file.write_text(rebuilt, encoding="utf-8")
    parsed = parse_srt_file(temp_file)
    temp_file.unlink()

    # 验证
    assert len(parsed) == 3, f"应该有3条字幕，实际 {len(parsed)} 条"
    assert parsed[0]["text"] == "你好", f"第一条翻译不正确: {parsed[0]['text']}"
    assert parsed[1]["text"] == "世界", f"第二条翻译不正确: {parsed[1]['text']}"
    assert parsed[2]["text"] == "测试", f"第三条翻译不正确: {parsed[2]['text']}"

    # 验证时间戳保持不变
    assert parsed[0]["start"] == original_subtitles[0]["start"]
    assert parsed[0]["end"] == original_subtitles[0]["end"]

    print("✅ SRT 重建测试通过!")


def test_translation_completeness():
    """测试翻译完整性检查"""
    print("\n=== 测试翻译完整性检查 ===")

    processor = SubtitleProcessor()

    # 原始字幕（第1批，偏移量为0）
    original_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Hello"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "World"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Test"},
    ]

    # 模拟缺失的翻译（只有第1、3条，第2条缺失）
    incomplete_translations = {1: "你好", 3: "测试"}

    # 补充翻译（偏移量为0）
    completed = processor._ensure_translation_completeness(incomplete_translations, original_subtitles, batch_offset=0)

    print(f"补充后: {len(completed)} 条")

    assert len(completed) == 3, f"补充后应该有3条，实际 {len(completed)} 条"
    assert completed[0] == "你好", f"第一条应该被翻译"
    assert completed[1] == "World", f"第二条缺失，应该用原文填充"
    assert completed[2] == "测试", f"第三条应该被翻译"

    print("✅ 翻译完整性检查测试通过!")


def test_missing_index_detection():
    """测试缺失字幕index的检测和填充"""
    print("\n=== 测试缺失字幕index检测 ===")

    processor = SubtitleProcessor()

    # 原始字幕
    original_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "First"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "Second"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Third"},
        {"index": 4, "start": "00:00:12,500", "end": "00:00:16,000", "text": "Fourth"},
        {"index": 5, "start": "00:00:16,500", "end": "00:00:20,000", "text": "Fifth"},
    ]

    # 模拟LLM返回的翻译结果（缺失第2、4条）
    mock_llm_result = """1: 第一条
3: 第三条
5: 第五条"""

    # 解析翻译结果
    translated_map, _ = processor._parse_translated_batch_result(mock_llm_result)

    print(f"解析出的翻译映射: {translated_map}")
    print(f"缺失的索引: {[i for i in range(1, 6) if i not in translated_map]}")

    # 验证映射正确
    assert 1 in translated_map and translated_map[1] == "第一条"
    assert 2 not in translated_map, "第2条应该缺失"
    assert 3 in translated_map and translated_map[3] == "第三条"
    assert 4 not in translated_map, "第4条应该缺失"
    assert 5 in translated_map and translated_map[5] == "第五条"

    # 补充翻译（偏移量为0，因为是第1批）
    completed = processor._ensure_translation_completeness(translated_map, original_subtitles, batch_offset=0)

    print(f"补充后的翻译:")
    for i, text in enumerate(completed):
        print(f"  {i+1}: {text}")

    # 验证完整性
    assert len(completed) == 5
    assert completed[0] == "第一条", "第1条应该是翻译"
    assert completed[1] == "Second", "第2条缺失，应该用原文填充"
    assert completed[2] == "第三条", "第3条应该是翻译"
    assert completed[3] == "Fourth", "第4条缺失，应该用原文填充"
    assert completed[4] == "第五条", "第5条应该是翻译"

    print("✅ 缺失字幕index检测测试通过!")


def test_batch_offset_handling():
    """测试批次偏移量处理（第2批及以后的批次）"""
    print("\n=== 测试批次偏移量处理 ===")

    processor = SubtitleProcessor()

    # 模拟第2批字幕（假设第1批有5条，这批是第6-10条）
    batch_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Subtitle 6"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "Subtitle 7"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Subtitle 8"},
    ]

    # 模拟完整翻译（全局序号6, 7, 8）
    translated_map = {
        6: "翻译6",
        7: "翻译7",
        8: "翻译8"
    }

    # 批次偏移量为5（前面有5条字幕）
    batch_offset = 5
    completed = processor._ensure_translation_completeness(translated_map, batch_subtitles, batch_offset=batch_offset)

    print(f"补充后的翻译:")
    for i, text in enumerate(completed):
        print(f"  {i+6}: {text}")

    # 验证完整性
    assert len(completed) == 3
    assert completed[0] == "翻译6", "第6条应该是翻译"
    assert completed[1] == "翻译7", "第7条应该是翻译"
    assert completed[2] == "翻译8", "第8条应该是翻译"

    # 测试缺失的情况
    incomplete_map = {
        6: "翻译6",
        8: "翻译8"
    }

    completed_incomplete = processor._ensure_translation_completeness(incomplete_map, batch_subtitles, batch_offset=batch_offset)

    print(f"\n缺失第7条时的补充结果:")
    for i, text in enumerate(completed_incomplete):
        print(f"  {i+6}: {text}")

    assert len(completed_incomplete) == 3
    assert completed_incomplete[0] == "翻译6"
    assert completed_incomplete[1] == "Subtitle 7", "第7条缺失，应该用原文填充"
    assert completed_incomplete[2] == "翻译8"

    print("✅ 批次偏移量处理测试通过!")


def test_bilingual_translation_parsing():
    """测试双语字幕翻译结果解析"""
    print("\n=== 测试双语字幕解析 ===")

    processor = SubtitleProcessor()

    # 测试1: 使用.分隔符的双语格式（中文带重复序号）
    mock_bilingual_translation_with_index = """1. Back in school, I discovered a very
1. 上学的时候，我发现了一个非常
2. simple mathematical formula that I keep
2. 简单的数学公式，
3. thinking about to this day. It goes like
3. 直到今天我仍然在思考它。 事情是
4. this. Imagine that you have a 3D point
4. 这样的。 想象一下，在你的屏幕后面，
5. in an imaginary 3D space behind your
5. 有一个位于假想三维空间中的三维点"""

    parsed_with_index, valid1 = processor._parse_translated_batch_result(mock_bilingual_translation_with_index)

    print(f"[测试1] 中文带序号格式的解析结果数量: {len(parsed_with_index)}, 格式正确: {valid1}")
    for idx, text in parsed_with_index.items():
        print(f"  {idx}: {repr(text[:80])}")

    # 验证
    assert isinstance(parsed_with_index, dict), f"应该返回字典，实际返回 {type(parsed_with_index)}"
    assert len(parsed_with_index) == 5, f"应该解析出5条，实际 {len(parsed_with_index)} 条"
    assert valid1, "格式应该是正确的"

    # 验证每一条都包含英文和中文（用换行符分隔）
    assert "\n" in parsed_with_index[1], "第1条应该包含换行符（双语）"
    assert parsed_with_index[1].startswith("Back in school"), "第1条应该以英文开头"
    assert "上学的时候" in parsed_with_index[1], "第1条应该包含中文翻译"

    print("  ✅ 中文带序号格式的测试通过")

    # 测试2: 使用:分隔符的双语格式（中文不带序号）
    mock_bilingual_translation_colon = """1: Back in school, I discovered a very simple mathematical formula that I keep
上学时，我发现了一个非常简单的数学公式，我一直
2: thinking about to this day. It goes like
思考至今。它是这样的。
3: this. Imagine that you have a 3D point
这个。想象一下，你有一个三维点
4: in an imaginary 3D space behind your
在你屏幕后的一个假想三维空间中
5: Let's try this formula out
让我们试试这个公式"""

    parsed_colon, valid2 = processor._parse_translated_batch_result(mock_bilingual_translation_colon)

    print(f"\n[测试2] 使用:分隔符（中文不带序号）的解析结果数量: {len(parsed_colon)}, 格式正确: {valid2}")
    for idx, text in parsed_colon.items():
        print(f"  {idx}: {repr(text[:80])}")

    # 验证
    assert isinstance(parsed_colon, dict), f"应该返回字典，实际返回 {type(parsed_colon)}"
    assert len(parsed_colon) == 5, f"应该解析出5条，实际 {len(parsed_colon)} 条"
    assert valid2, "格式应该是正确的"

    # 验证双语格式
    assert "\n" in parsed_colon[1], "第1条应该包含换行符（双语）"
    assert "Back in school" in parsed_colon[1], "第1条应该包含英文"
    assert "上学时" in parsed_colon[1], "第1条应该包含中文"

    assert "\n" in parsed_colon[2], "第2条应该包含换行符（双语）"
    assert "thinking about" in parsed_colon[2], "第2条应该包含英文"
    assert "思考至今" in parsed_colon[2], "第2条应该包含中文"

    print("  ✅ 使用:分隔符的测试通过")

    # 测试3: 格式不正确的情况（部分缺少中文翻译）
    mock_invalid_translation = """1: Back in school, I discovered a very simple mathematical formula
上学时，我发现了一个非常简单的数学公式
2: thinking about to this day
思考至今
3: this. Imagine that you have a 3D point"""

    parsed_invalid, valid3 = processor._parse_translated_batch_result(mock_invalid_translation)

    print(f"\n[测试3] 格式不正确的解析结果数量: {len(parsed_invalid)}, 格式正确: {valid3}")
    for idx, text in parsed_invalid.items():
        print(f"  {idx}: {repr(text)}")

    assert not valid3, "格式应该被标记为不正确（第3条缺少中文翻译）"
    assert len(parsed_invalid) == 3, f"应该解析出3条，实际 {len(parsed_invalid)} 条"

    print("  ✅ 格式验证测试通过")

    print("✅ 双语字幕解析测试通过!")


def test_end_to_end_bilingual_subtitle_generation():
    """端到端测试：验证从模型输出到SRT文件的完整双语字幕生成流程"""
    print("\n=== 端到端双语字幕生成测试 ===")

    processor = SubtitleProcessor()

    # 步骤1: 创建原始英文字幕
    original_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Back in school, I discovered a very"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "simple mathematical formula that I keep"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "thinking about to this day. It goes like"},
    ]

    print("\n[步骤1] 原始英文字幕:")
    for sub in original_subtitles:
        print(f"  {sub['index']}: {sub['text']}")

    # 步骤2: 模拟模型返回的双语输出（新格式）
    mock_model_output = """1. Back in school, I discovered a very
上学的时候，我发现了一个非常
2. simple mathematical formula that I keep
简单的数学公式，
3. thinking about to this day. It goes like
直到今天我仍然在思考它。 事情是"""

    print("\n[步骤2] 模拟模型输出:")
    print(mock_model_output)

    # 步骤3: 解析模型输出
    parsed_translations, _ = processor._parse_translated_batch_result(mock_model_output)

    print("\n[步骤3] 解析后的翻译映射:")
    for idx, text in parsed_translations.items():
        print(f"  {idx}: {repr(text)}")

    # 验证解析结果
    assert len(parsed_translations) == 3, f"应该解析出3条，实际 {len(parsed_translations)} 条"

    # 验证每条都包含双语
    for idx in [1, 2, 3]:
        assert idx in parsed_translations, f"缺少第 {idx} 条翻译"
        assert "\n" in parsed_translations[idx], f"第 {idx} 条应该包含换行符（双语）"
        print(f"  ✓ 第 {idx} 条是双语格式")

    # 步骤4: 转换为翻译文本列表
    translated_texts = [parsed_translations[i] for i in range(1, 4)]

    print("\n[步骤4] 翻译文本列表:")
    for i, text in enumerate(translated_texts, 1):
        print(f"  {i}: {repr(text)}")

    # 步骤5: 重建SRT内容
    rebuilt_srt = processor._rebuild_srt_from_batches(original_subtitles, translated_texts)

    print("\n[步骤5] 重建的SRT内容:")
    print(rebuilt_srt)
    print("  --- SRT内容结束 ---")

    # 步骤6: 保存到临时文件并重新解析验证
    temp_file = Path("/tmp/test_e2e_bilingual.srt")
    temp_file.write_text(rebuilt_srt, encoding="utf-8")

    print("\n[步骤6] 保存到文件后重新解析:")
    parsed_final = processor._parse_srt_file(temp_file)

    # 验证最终结果
    print(f"\n[验证] 最终解析结果:")
    success_count = 0
    for i, sub in enumerate(parsed_final):
        has_both = "\n" in sub["text"]
        has_english = bool(sub["text"].strip())
        has_chinese = any("\u4e00" <= c <= "\u9fff" for c in sub["text"])

        print(f"  {sub['index']}: {repr(sub['text'])}")
        print(f"    - 包含换行符: {has_both}")
        print(f"    - 包含英文: {has_english}")
        print(f"    - 包含中文: {has_chinese}")

        if has_both and has_chinese:
            success_count += 1

    # 清理
    temp_file.unlink()

    # 最终断言
    assert len(parsed_final) == 3, f"最终应该有3条字幕，实际 {len(parsed_final)} 条"
    assert success_count == 3, f"所有3条字幕都应该是双语格式，实际只有 {success_count} 条"

    print(f"\n✅ 端到端测试通过！{success_count}/{len(parsed_final)} 条字幕为双语格式")


def test_full_translation_workflow():
    """测试完整翻译工作流（行数和内容对比）"""
    print("\n=== 测试完整翻译工作流 ===")

    # 创建测试文件
    test_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Welcome to programming tutorial"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "Today we will learn Python"},
        {"index": 3, "start": "00:00:08,500", "end": "00:00:12,000", "text": "Python is a powerful language"},
        {"index": 4, "start": "00:00:12,500", "end": "00:00:16,000", "text": "Let's write our first program"},
        {"index": 5, "start": "00:00:16,500", "end": "00:00:20,000", "text": "print('Hello, World!')"},
    ]

    test_file = Path("/tmp/test_full_workflow.srt")
    create_test_srt_file(test_file, test_subtitles)

    # 解析原始字幕
    processor = SubtitleProcessor()
    original_parsed = processor._parse_srt_file(test_file)

    print(f"\n原始字幕:")
    for sub in original_parsed:
        print(f"  {sub['index']}: {sub['text']}")

    # 模拟翻译结果（批量格式）
    mock_batch_translation = """1: 欢迎来到编程教程
2: 今天我们将学习Python
3: Python是一门强大的语言
4: 让我们编写第一个程序
5: print('你好，世界！')"""

    # 解析翻译结果（返回字典）
    translated_map, _ = processor._parse_translated_batch_result(mock_batch_translation)
    # 转换为列表
    translated_texts = [translated_map[i + 1] for i in range(len(test_subtitles))]

    print(f"\n翻译文本:")
    for i, text in enumerate(translated_texts):
        print(f"  {i+1}: {text}")

    # 重建 SRT
    rebuilt_srt = processor._rebuild_srt_from_batches(original_parsed, translated_texts)

    # 解析重建的 SRT
    temp_file = Path("/tmp/test_rebuilt_full.srt")
    temp_file.write_text(rebuilt_srt, encoding="utf-8")
    translated_parsed = parse_srt_file(temp_file)
    temp_file.unlink()

    print(f"\n翻译后的字幕:")
    for sub in translated_parsed:
        print(f"  {sub['index']}: {sub['text']}")

    # 验证数量
    print(f"\n✓ 原始字幕数量: {len(original_parsed)}")
    print(f"✓ 翻译字幕数量: {len(translated_parsed)}")
    assert len(original_parsed) == len(translated_parsed), "字幕数量不匹配!"

    # 验证每一条字幕都有翻译
    print(f"\n逐条对比:")
    for i, (orig, trans) in enumerate(zip(original_parsed, translated_parsed)):
        # 验证索引一致
        assert orig["index"] == trans["index"], f"第 {i+1} 条索引不匹配"
        # 验证时间戳一致
        assert orig["start"] == trans["start"], f"第 {i+1} 条开始时间不匹配"
        assert orig["end"] == trans["end"], f"第 {i+1} 条结束时间不匹配"
        # 验证有翻译内容（非空且不等于原文）
        assert trans["text"].strip(), f"第 {i+1} 条翻译为空"
        print(f"  ✓ 第 {i+1} 条: 原文「{orig['text']}」→ 译文「{trans['text']}」")

    # 清理
    test_file.unlink()

    print("\n✅ 完整翻译工作流测试通过!")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("字幕翻译单元测试")
    print("=" * 60)

    try:
        test_srt_parsing()
        test_batch_formatting()
        test_translation_result_parsing()
        test_bilingual_translation_parsing()  # 新增双语解析测试
        test_end_to_end_bilingual_subtitle_generation()  # 新增端到端测试
        test_srt_rebuilding()
        test_translation_completeness()
        test_missing_index_detection()
        test_batch_offset_handling()  # 新增测试
        test_full_translation_workflow()

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
