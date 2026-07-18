"""字幕翻译缓存功能单元测试"""

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


def test_get_cache_path():
    """测试获取缓存路径"""
    print("\n=== 测试获取缓存路径 ===")

    processor = SubtitleProcessor()

    # 测试各种输出路径
    test_cases = [
        (Path("/data/video/zh.srt"), Path("/data/video/zh.cache.json")),
        (Path("/tmp/subtitle.srt"), Path("/tmp/subtitle.cache.json")),
        (Path("/home/user/test.srt"), Path("/home/user/test.cache.json")),
    ]

    for output_path, expected_cache_path in test_cases:
        cache_path = processor._get_subtitle_cache_path(output_path)
        assert cache_path == expected_cache_path, f"缓存路径不匹配: {cache_path} != {expected_cache_path}"
        print(f"✓ {output_path} -> {cache_path}")

    print("✅ 缓存路径测试通过!")


def test_calculate_subtitle_hash():
    """测试字幕哈希计算"""
    print("\n=== 测试字幕哈希计算 ===")

    processor = SubtitleProcessor()

    # 创建测试字幕
    test_subtitles = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:04,000", "text": "Hello, world!"},
        {"index": 2, "start": "00:00:04,500", "end": "00:00:08,000", "text": "This is a test."},
    ]

    test_file = Path("/tmp/test_hash.srt")
    create_test_srt_file(test_file, test_subtitles)

    # 计算哈希
    hash1 = processor._calculate_subtitle_hash(test_file)
    print(f"哈希值: {hash1}")

    # 再次计算哈希，应该相同
    hash2 = processor._calculate_subtitle_hash(test_file)
    assert hash1 == hash2, "相同文件的哈希值应该相同"

    # 修改文件内容，哈希应该改变
    test_subtitles[0]["text"] = "Modified text"
    create_test_srt_file(test_file, test_subtitles)
    hash3 = processor._calculate_subtitle_hash(test_file)
    assert hash1 != hash3, "不同文件的哈希值应该不同"

    print(f"✓ 相同文件哈希相同: {hash1 == hash2}")
    print(f"✓ 不同文件哈希不同: {hash1 != hash3}")

    # 清理
    test_file.unlink()

    print("✅ 哈希计算测试通过!")


def test_save_and_load_cache():
    """测试缓存保存和加载"""
    print("\n=== 测试缓存保存和加载 ===")

    processor = SubtitleProcessor()

    cache_path = Path("/tmp/test_cache.json")

    # 清理可能存在的旧缓存
    if cache_path.exists():
        cache_path.unlink()

    # 创建测试数据
    subtitle_hash = "abc123"
    total_subtitles = 30
    batch_size = 10
    translated_batches = {
        0: ["翻译1", "翻译2", "翻译3", "翻译4", "翻译5", "翻译6", "翻译7", "翻译8", "翻译9", "翻译10"],
        1: ["翻译11", "翻译12", "翻译13", "翻译14", "翻译15", "翻译16", "翻译17", "翻译18", "翻译19", "翻译20"],
    }

    # 保存缓存
    processor._save_translation_cache(
        cache_path, subtitle_hash, total_subtitles, batch_size, translated_batches
    )

    assert cache_path.exists(), "缓存文件应该存在"
    print(f"✓ 缓存文件已创建: {cache_path}")

    # 加载缓存
    loaded_cache = processor._load_translation_cache(cache_path, subtitle_hash, total_subtitles, batch_size)

    assert loaded_cache is not None, "缓存应该能成功加载"
    assert loaded_cache["subtitle_hash"] == subtitle_hash, "哈希值不匹配"
    assert loaded_cache["total_subtitles"] == total_subtitles, "字幕总数不匹配"
    assert loaded_cache["batch_size"] == batch_size, "批次大小不匹配"
    assert len(loaded_cache["translated_batches"]) == 2, "批次数量不匹配"

    print(f"✓ 缓存加载成功: {len(loaded_cache['translated_batches'])} 批")

    # 清理
    cache_path.unlink()

    print("✅ 缓存保存和加载测试通过!")


def test_cache_validation():
    """测试缓存验证（哈希不匹配、总数不匹配等）"""
    print("\n=== 测试缓存验证 ===")

    processor = SubtitleProcessor()

    cache_path = Path("/tmp/test_cache_validation.json")

    # 清理可能存在的旧缓存
    if cache_path.exists():
        cache_path.unlink()

    # 创建测试数据
    subtitle_hash = "abc123"
    total_subtitles = 30
    batch_size = 10
    translated_batches = {
        0: ["翻译1", "翻译2", "翻译3", "翻译4", "翻译5", "翻译6", "翻译7", "翻译8", "翻译9", "翻译10"],
    }

    # 保存缓存
    processor._save_translation_cache(
        cache_path, subtitle_hash, total_subtitles, batch_size, translated_batches
    )

    # 测试1: 哈希不匹配
    loaded_cache = processor._load_translation_cache(cache_path, "wrong_hash", total_subtitles, batch_size)
    assert loaded_cache is None, "哈希不匹配时应该返回 None"
    print("✓ 哈希不匹配验证通过")

    # 测试2: 总数不匹配
    loaded_cache = processor._load_translation_cache(cache_path, subtitle_hash, 50, batch_size)
    assert loaded_cache is None, "总数不匹配时应该返回 None"
    print("✓ 总数不匹配验证通过")

    # 测试3: 批次大小不匹配
    loaded_cache = processor._load_translation_cache(cache_path, subtitle_hash, total_subtitles, 15)
    assert loaded_cache is None, "批次大小不匹配时应该返回 None"
    print("✓ 批次大小不匹配验证通过")

    # 测试4: 所有参数正确
    loaded_cache = processor._load_translation_cache(cache_path, subtitle_hash, total_subtitles, batch_size)
    assert loaded_cache is not None, "所有参数正确时应该成功加载"
    print("✓ 所有参数正确时加载成功")

    # 清理
    cache_path.unlink()

    print("✅ 缓存验证测试通过!")


def test_update_cache():
    """测试缓存更新"""
    print("\n=== 测试缓存更新 ===")

    processor = SubtitleProcessor()

    cache_path = Path("/tmp/test_cache_update.json")

    # 清理可能存在的旧缓存
    if cache_path.exists():
        cache_path.unlink()

    # 创建初始缓存
    subtitle_hash = "abc123"
    total_subtitles = 30
    batch_size = 10

    cache_data = {
        "subtitle_hash": subtitle_hash,
        "total_subtitles": total_subtitles,
        "batch_size": batch_size,
        "translated_batches": {},
    }

    # 更新第一批
    batch_0_translations = ["翻译1", "翻译2", "翻译3", "翻译4", "翻译5", "翻译6", "翻译7", "翻译8", "翻译9", "翻译10"]
    processor._update_translation_cache(cache_path, cache_data, 0, batch_0_translations)

    assert cache_path.exists(), "缓存文件应该存在"
    print(f"✓ 缓存文件已创建")

    # 验证第一批
    loaded_cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "0" in loaded_cache["translated_batches"], "应该包含批次0"
    assert loaded_cache["translated_batches"]["0"] == batch_0_translations, "批次0内容不匹配"
    print(f"✓ 批次0更新成功")

    # 更新第二批
    batch_1_translations = ["翻译11", "翻译12", "翻译13", "翻译14", "翻译15", "翻译16", "翻译17", "翻译18", "翻译19", "翻译20"]
    processor._update_translation_cache(cache_path, cache_data, 1, batch_1_translations)

    # 验证第二批
    loaded_cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "0" in loaded_cache["translated_batches"], "应该包含批次0"
    assert "1" in loaded_cache["translated_batches"], "应该包含批次1"
    assert loaded_cache["translated_batches"]["1"] == batch_1_translations, "批次1内容不匹配"
    print(f"✓ 批次1更新成功")

    # 清理
    cache_path.unlink()

    print("✅ 缓存更新测试通过!")


def test_clear_cache():
    """测试缓存清除"""
    print("\n=== 测试缓存清除 ===")

    processor = SubtitleProcessor()

    cache_path = Path("/tmp/test_cache_clear.json")

    # 创建测试缓存
    cache_path.write_text("test", encoding="utf-8")
    assert cache_path.exists(), "缓存文件应该存在"

    # 清除缓存
    processor._clear_translation_cache(cache_path)
    assert not cache_path.exists(), "缓存文件应该被删除"
    print("✓ 缓存文件已清除")

    # 清理不存在的缓存（不应该报错）
    processor._clear_translation_cache(cache_path)
    print("✓ 清除不存在的缓存不会报错")

    print("✅ 缓存清除测试通过!")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("字幕翻译缓存功能单元测试")
    print("=" * 60)

    test_get_cache_path()
    test_calculate_subtitle_hash()
    test_save_and_load_cache()
    test_cache_validation()
    test_update_cache()
    test_clear_cache()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
