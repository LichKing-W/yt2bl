"""测试中文字幕样式"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.subtitle_processor import SubtitleProcessor


def test_chinese_subtitle_style():
    """测试中文字幕样式生成"""
    print("\n=== 测试中文字幕样式 ===")

    processor = SubtitleProcessor()

    # 创建双语测试字幕
    test_srt = """1
00:00:01,000 --> 00:00:04,000
欢迎来到编程教程

2
00:00:04,500 --> 00:00:08,000
Welcome to programming tutorial
Today we will learn Python

3
00:00:08,500 --> 00:00:12,000
Python是一门强大的语言
It is widely used in data science

4
00:00:12,500 --> 00:00:16,000
让我们一起开始学习吧
Let's start coding together!
"""

    # 创建测试文件
    test_file = Path("/tmp/test_bilingual.srt")
    test_file.write_text(test_srt, encoding="utf-8")

    # 转换为 ASS
    ass_file = processor.convert_srt_to_ass(test_file, zh_font_size=24, en_font_size=18)

    # 读取并验证 ASS 文件
    ass_content = ass_file.read_text(encoding="utf-8-sig")

    print(f"\n生成的 ASS 文件内容:")
    print("=" * 60)
    print(ass_content)
    print("=" * 60)

    # 验证 Chinese 样式
    assert "Style: Chinese" in ass_content, "缺少 Chinese 样式定义"
    assert "VYuan_Round" in ass_content, "未使用圆体字体"
    assert "&H00FFFFFF" in ass_content, "未设置白色字体"
    assert "&H000000FF" in ass_content, "未设置蓝色描边"

    # 验证中文字幕使用 Chinese 样式
    assert "Dialogue: 0,0:00:01.00,0:00:04.00,Chinese" in ass_content, "第一行中文未使用 Chinese 样式"
    assert "欢迎来到编程教程" in ass_content, "缺少中文内容"

    # 验证英文字幕使用 Default 样式
    assert "Dialogue: 0,0:00:04.50,0:00:08.00,Default" in ass_content, "第二行英文未使用 Default 样式"
    assert "Welcome to programming tutorial" in ass_content or "Welcome" in ass_content, "缺少英文内容"

    print("\n✅ 中文字幕样式验证通过!")
    print("\n样式说明:")
    print("  - 中文名称: Chinese")
    print("  - 字体: VYuan_Round (圆体)")
    print("  - 字号: 24")
    print("  - 颜色: 白色 (&H00FFFFFF)")
    print("  - 描边: 蓝色 (&H000000FF), 宽度 3")
    print("  - 英文样式: Default, Arial, 18号")

    # 清理
    test_file.unlink()
    ass_file.unlink()

    return True


if __name__ == "__main__":
    try:
        test_chinese_subtitle_style()
        print("\n✅ 测试完成!")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
