"""字幕处理模块"""

import asyncio
import hashlib
import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.config import settings
from ..utils.llm_client import llm_complete
from ..utils.logger import logger


class SubtitleProcessor:
    """字幕处理器"""

    def __init__(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / "youtube_to_bilibili_subtitles"
        self.temp_dir.mkdir(exist_ok=True)
        # 项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        self.prompts_dir = self.project_root / "prompts"

    async def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            logger.info("字幕临时文件清理完成")
        except Exception as e:
            logger.error(f"清理字幕临时文件失败: {str(e)}")

    def _srt_time_to_ms(self, time_str: str) -> int:
        """将SRT时间格式转换为毫秒

        Args:
            time_str: SRT时间格式 (00:00:00,000)

        Returns:
            毫秒数
        """
        hours = int(time_str[0:2])
        minutes = int(time_str[3:5])
        seconds = int(time_str[6:8])
        milliseconds = int(time_str[9:12])
        return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds

    def _ms_to_srt_time(self, ms: int) -> str:
        """将毫秒转换为SRT时间格式

        Args:
            ms: 毫秒数

        Returns:
            SRT时间格式 (00:00:00,000)
        """
        milliseconds = ms % 1000
        ms = ms // 1000
        seconds = ms % 60
        ms = ms // 60
        minutes = ms % 60
        hours = ms // 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def fix_subtitle_overlaps(self, srt_path: Path, fps: float = 60.0) -> Path:
        """修复字幕时间轴重叠问题

        Args:
            srt_path: SRT字幕文件路径
            fps: 帧率，用于计算最小间隔

        Returns:
            修复后的字幕文件路径
        """
        try:
            logger.info(f"正在修复字幕时间轴重叠: {srt_path.name}")

            # 解析字幕
            subtitles = self._parse_srt_file(srt_path)

            # 修复重叠
            for i in range(len(subtitles) - 1):
                current_end = self._srt_time_to_ms(subtitles[i]["end"])
                next_start = self._srt_time_to_ms(subtitles[i + 1]["start"])

                if current_end >= next_start:
                    # 调整当前字幕的结束时间，与下一条字幕间隔1帧
                    new_end_ms = next_start - int(1000 / fps)
                    subtitles[i]["end"] = self._ms_to_srt_time(new_end_ms)
                    logger.debug(
                        f"修复重叠: 字幕{i + 1}结束时间调整为 {subtitles[i]['end']}"
                    )

            # 生成输出路径
            output_path = srt_path.parent / f"{srt_path.stem}_fixed{srt_path.suffix}"

            # 写入修复后的字幕
            self._write_srt_file(subtitles, output_path)

            logger.info(f"字幕时间轴修复完成: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"修复字幕时间轴失败: {str(e)}")
            raise

    def merge_subtitle_lines(self, srt_path: Path) -> Path:
        """将字幕每两行合并为一行

        合并规则：
        - 使用第一行的开始时间
        - 使用第二行的结束时间
        - 文本内容合并，中间用空格分隔
        - 如果合并后的单词数>15，则不合并，作为单独一行

        Args:
            srt_path: SRT字幕文件路径

        Returns:
            合并后的字幕文件路径
        """
        try:
            logger.info(f"正在合并字幕行: {srt_path.name}")

            # 解析字幕
            subtitles = self._parse_srt_file(srt_path)

            # 每两行合并为一行，但检查单词数
            merged_subtitles = []
            i = 0
            while i < len(subtitles):
                if i + 1 < len(subtitles):
                    # 有两行，检查是否应该合并
                    sub1 = subtitles[i]
                    sub2 = subtitles[i + 1]

                    # 计算合并后的单词数
                    merged_text = f"{sub1['text']} {sub2['text']}"
                    word_count = self._count_words(merged_text)

                    if word_count > 15:
                        # 合并后单词数过多，不合并
                        logger.debug(
                            f"合并后单词数过多({word_count}个)，不合并字幕{i + 1}和{i + 2}"
                        )
                        # 添加第一行
                        merged_sub = {
                            "index": len(merged_subtitles) + 1,
                            "start": sub1["start"],
                            "end": sub1["end"],
                            "text": sub1["text"],
                        }
                        merged_subtitles.append(merged_sub)
                        # 下一轮将处理第二行
                        i += 1
                    else:
                        # 正常合并两行
                        merged_sub = {
                            "index": len(merged_subtitles) + 1,
                            "start": sub1["start"],
                            "end": sub2["end"],
                            "text": merged_text,
                        }
                        merged_subtitles.append(merged_sub)
                        logger.debug(
                            f"合并: 字幕{i + 1}和{i + 2} -> 字幕{len(merged_subtitles)} ({word_count}个单词)"
                        )
                        i += 2
                else:
                    # 只剩一行，直接添加
                    sub = subtitles[i]
                    merged_sub = {
                        "index": len(merged_subtitles) + 1,
                        "start": sub["start"],
                        "end": sub["end"],
                        "text": sub["text"],
                    }
                    merged_subtitles.append(merged_sub)
                    logger.debug(f"保留: 字幕{i + 1}（无法配对）")
                    i += 1

            # 生成输出路径
            output_path = srt_path.parent / f"{srt_path.stem}_merged{srt_path.suffix}"

            # 写入合并后的字幕
            self._write_srt_file(merged_subtitles, output_path)

            logger.info(
                f"字幕行合并完成: {output_path.name} (从{len(subtitles)}行合并为{len(merged_subtitles)}行)"
            )
            return output_path

        except Exception as e:
            logger.error(f"合并字幕行失败: {str(e)}")
            raise

    def _count_words(self, text: str) -> int:
        """计算文本中的单词数量（按空格分割）

        Args:
            text: 待统计的文本

        Returns:
            单词数量
        """
        # 使用正则表达式分割单词，处理连续空格和标点符号
        words = re.findall(r"\b[\w-]+\b", text)
        return len(words)

    def _write_srt_file(
        self, subtitles: List[Dict[str, Any]], output_path: Path
    ) -> None:
        """写入SRT字幕文件

        Args:
            subtitles: 字幕列表
            output_path: 输出文件路径
        """
        lines = []
        for sub in subtitles:
            lines.append(str(sub["index"]))
            lines.append(f"{sub['start']} --> {sub['end']}")
            lines.append(sub["text"])
            lines.append("")  # 空行分隔

        output_path.write_text("\n".join(lines), encoding="utf-8")

    async def translate_with_openai(
        self, subtitle_path: Path, output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """使用OpenAI API翻译字幕文件

        Args:
            subtitle_path: 字幕文件路径
            output_path: 输出文件路径，如果为None则自动生成

        Returns:
            翻译后的字幕文件路径
        """
        try:
            logger.info(f"开始使用LLM翻译字幕: {subtitle_path.name}")

            # 提取基础文件名（去掉语言代码，如 .en.srt -> base）
            # 例如: "video.en.srt" -> "video"
            original_stem = subtitle_path.stem  # 例如: "video.en"

            # 去掉语言代码后缀（如 .en, .zh-Hans 等）
            base_stem = original_stem
            for lang_suffix in [".en", ".eng", ".zh-Hans", ".zh-Hant", ".zh", ".zh-CN"]:
                if original_stem.lower().endswith(lang_suffix.lower()):
                    base_stem = original_stem[: -len(lang_suffix)]
                    break

            logger.info(f"基础文件名: {base_stem}")

            # 步骤1: 修复字幕时间轴重叠（生成临时文件）
            logger.info("步骤 1/4: 修复字幕时间轴重叠...")
            fixed_subtitle_path = self.fix_subtitle_overlaps(subtitle_path)

            # 步骤2: 合并字幕行（每两行合并为一行），保留原文件
            logger.info("步骤 2/4: 合并字幕行...")
            merged_subtitle_path = self.merge_subtitle_lines(fixed_subtitle_path)

            # 删除临时的fixed文件
            fixed_subtitle_path.unlink()
            logger.info(f"预处理字幕完成: {merged_subtitle_path.name}")

            # 检查OpenAI API密钥
            api_key = settings.openai_api_key
            if not api_key:
                logger.error("未设置OPENAI_API_KEY环境变量")
                return None

            # 获取base_url（可选）
            base_url = settings.openai_base_url

            # 获取模型配置
            model = settings.openai_model

            # 读取prompt模板
            prompt_path = self.prompts_dir / "translate.md"
            if not prompt_path.exists():
                logger.error(f"Prompt文件不存在: {prompt_path}")
                return None

            prompt_template = prompt_path.read_text(encoding="utf-8")

            # 解析字幕为结构化数据（使用预处理后的文件）
            subtitles = self._parse_srt_file(merged_subtitle_path)
            total_subtitles = len(subtitles)
            logger.info(f"解析到 {total_subtitles} 条字幕")

            # 生成输出路径（统一为 zh.srt）
            if output_path is None:
                output_path = subtitle_path.parent / "zh.srt"

            # 分批翻译
            batch_size = 10
            all_translated_texts = []

            total_batches = (total_subtitles + batch_size - 1) // batch_size

            # 计算字幕哈希值，用于缓存验证
            subtitle_hash = self._calculate_subtitle_hash(merged_subtitle_path)

            # 尝试加载翻译缓存
            cache_path = self._get_subtitle_cache_path(output_path)
            cache_data = self._load_translation_cache(
                cache_path, subtitle_hash, total_subtitles, batch_size
            )

            # 从缓存中恢复已翻译的批次
            translated_batches = {}  # {批次索引: [翻译文本列表]}
            start_batch_index = 0  # 从第几批开始翻译

            if cache_data:
                # 有缓存，从缓存中恢复
                translated_batches = {
                    int(k): v
                    for k, v in cache_data.get("translated_batches", {}).items()
                }
                start_batch_index = len(translated_batches)
                logger.info(f"从缓存恢复，将从第 {start_batch_index + 1} 批开始翻译")

                # 将缓存中的翻译文本展开到 all_translated_texts
                for batch_idx in sorted(translated_batches.keys()):
                    all_translated_texts.extend(translated_batches[batch_idx])

            logger.info(
                f"步骤 3/4: 正在分批翻译字幕，共 {total_subtitles} 条，分 {total_batches} 批"
            )

            try:
                for i in range(0, total_subtitles, batch_size):
                    batch_num = i // batch_size + 1
                    batch_index = batch_num - 1  # 批次索引（从0开始）

                    # 如果该批次已在缓存中，跳过
                    if batch_index < start_batch_index:
                        logger.info(f"跳过第 {batch_num}/{total_batches} 批（已缓存）")
                        continue

                    end_idx = min(i + batch_size, total_subtitles)
                    batch_subtitles = subtitles[i:end_idx]

                    logger.info(
                        f"翻译第 {batch_num}/{total_batches} 批 ({i + 1}-{end_idx} 条)..."
                    )

                    # 重试机制：最多重试5次
                    max_retries = 5
                    translated_map = {}
                    retry_count = 0
                    format_valid = False

                    while retry_count < max_retries:
                        if retry_count > 0:
                            logger.info(
                                f"第 {batch_num} 批第 {retry_count}/{max_retries} 次重试，重新翻译整个批次..."
                            )

                        # 格式化当前批次的字幕（始终翻译整个批次）
                        batch_text = self._format_subtitles_for_translation_batch(
                            batch_subtitles, i
                        )

                        # 调用API翻译当前批次
                        translated_batch = await self._call_openai_translate(
                            prompt_template, batch_text, api_key, base_url, model
                        )

                        # 解析翻译结果（返回字典和格式是否正确的标志）
                        current_translated_map, current_format_valid = (
                            self._parse_translated_batch_result(translated_batch)
                        )

                        # 如果这次返回的结果更好（数量更多）或格式正确，使用这次的结果
                        if len(current_translated_map) > len(translated_map):
                            translated_map = current_translated_map
                            format_valid = current_format_valid

                        retry_count += 1

                        # 检查是否完整且格式正确
                        if len(translated_map) == len(batch_subtitles) and format_valid:
                            logger.info(
                                f"第 {batch_num} 批翻译完整且格式正确，共 {len(translated_map)} 条"
                            )
                            break
                        elif retry_count < max_retries:
                            if not format_valid:
                                logger.warning(
                                    f"第 {batch_num} 批翻译格式不正确（部分字幕缺失中文翻译），将进行第 {retry_count + 1} 次重试"
                                )
                            else:
                                missing = [
                                    j + 1
                                    for j in range(len(batch_subtitles))
                                    if (j + 1) not in translated_map
                                ]
                                logger.warning(
                                    f"第 {batch_num} 批翻译不完整，已翻译 {len(translated_map)}/{len(batch_subtitles)} 条，缺失序号: {missing}，将进行第 {retry_count + 1} 次重试"
                                )

                    # 重试结束后仍不完整的，用原文填充
                    if len(translated_map) < len(batch_subtitles):
                        missing_indices = [
                            j + 1
                            for j in range(len(batch_subtitles))
                            if (j + 1) not in translated_map
                        ]
                        logger.error(
                            f"第 {batch_num} 批重试 {max_retries} 次后仍缺失 {len(missing_indices)} 条，将使用原文填充: {missing_indices}"
                        )

                    # 确保当前批次完整性
                    translated_texts = self._ensure_translation_completeness(
                        translated_map, batch_subtitles, batch_offset=i
                    )
                    all_translated_texts.extend(translated_texts)

                    # 保存当前批次到缓存
                    if cache_data is None:
                        # 首次创建缓存
                        cache_data = {
                            "subtitle_hash": subtitle_hash,
                            "total_subtitles": total_subtitles,
                            "batch_size": batch_size,
                            "translated_batches": {},
                        }
                    self._update_translation_cache(
                        cache_path, cache_data, batch_index, translated_texts
                    )

                    logger.info(
                        f"第 {batch_num}/{total_batches} 批翻译完成，翻译了 {len(translated_texts)} 条"
                    )

                # 最终验证翻译完整性（由于每批已经保证完整性，这里只是双重检查）
                if len(all_translated_texts) != total_subtitles:
                    logger.error(
                        f"翻译数量不匹配: 原文 {total_subtitles} 条，译文 {len(all_translated_texts)} 条"
                    )
                    # 使用全局字幕列表填充
                    global_translated_map = {
                        i + 1: text for i, text in enumerate(all_translated_texts)
                    }
                    all_translated_texts = self._ensure_translation_completeness(
                        global_translated_map, subtitles
                    )

                # 重建 SRT 文件
                logger.info("步骤 4/4: 重建字幕文件...")
                final_content = self._rebuild_srt_from_batches(
                    subtitles, all_translated_texts
                )

                # 保存翻译结果
                output_path.write_text(final_content, encoding="utf-8")

                # 删除临时的预处理文件
                merged_subtitle_path.unlink()

                # 清除翻译缓存（翻译成功后）
                self._clear_translation_cache(cache_path)

                logger.info(f"字幕翻译完成: {output_path.name}")
                return output_path

            except Exception as e:
                logger.error(f"翻译失败: {str(e)}")
                import traceback

                logger.error(traceback.format_exc())
                return None

        except Exception as e:
            logger.error(f"OpenAI字幕翻译失败: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return None

    def _parse_srt_file(self, srt_path: Path) -> List[Dict[str, Any]]:
        """解析 SRT 字幕文件为结构化数据

        Returns:
            字幕条目列表，每条包含 index, start, end, text
        """
        content = srt_path.read_text(encoding="utf-8")
        entries = []

        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                try:
                    index = int(lines[0].strip())
                    time_line = lines[1].strip()
                    text = "\n".join(lines[2:])

                    time_parts = time_line.split("-->")
                    if len(time_parts) == 2:
                        start = time_parts[0].strip()
                        end = time_parts[1].strip()

                        entries.append(
                            {"index": index, "start": start, "end": end, "text": text}
                        )
                except (ValueError, IndexError) as e:
                    logger.debug(f"解析字幕块失败: {block[:50]}... 错误: {e}")
                    continue

        return entries

    def _format_subtitles_for_translation_batch(
        self, subtitles: List[Dict[str, Any]], offset: int
    ) -> str:
        """格式化字幕批次用于翻译

        将字幕文本中的多行内容合并成一行，确保翻译时格式正确。
        """
        lines = []
        for i, sub in enumerate(subtitles):
            seq_num = offset + i + 1
            # 将多行文本合并成一行，使用正则表达式将连续空白字符替换为单个空格
            text = re.sub(r"\s+", " ", sub["text"].strip())
            lines.append(f"{seq_num}: {text}")
        return "\n".join(lines)

    def _parse_translated_batch_result(
        self, translated_text: str
    ) -> Tuple[Dict[int, str], bool]:
        """解析批次翻译结果，返回 {序号: 双语文本} 的字典和格式是否正确的标志

        支持多种格式：
        1. 旧格式（纯中文）：1: 翻译文本
        2. 双语格式（使用.或:）：1. English text
           1. 中文翻译（带重复序号）
           或：1: English text
           中文翻译（不带序号）

        Returns:
            (翻译映射字典, 格式是否正确 - 所有字幕都包含双语)
        """
        lines = translated_text.split("\n")

        translated_map = {}  # {序号: 双语文本}
        format_valid = True  # 格式是否正确
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行和注释行
            if (
                not line
                or line.startswith("#")
                or line.startswith("Note")
                or line.startswith("注意")
            ):
                i += 1
                continue

            # 检查序号行（使用.或:作为分隔符）
            index = None
            first_part_text = None
            separator = None

            # 尝试.分隔符
            if ". " in line:
                parts = line.split(". ", 1)
                index_str = parts[0].strip()
                if index_str.isdigit():
                    separator = "."
                    index = int(index_str)
                    first_part_text = parts[1].strip() if len(parts) > 1 else ""

            # 尝试:分隔符（如果.没找到）
            if index is None and ": " in line:
                parts = line.split(": ", 1)
                index_str = parts[0].strip()
                if index_str.isdigit():
                    separator = ":"
                    index = int(index_str)
                    first_part_text = parts[1].strip() if len(parts) > 1 else ""

            # 如果找到了序号行
            if index is not None and first_part_text:
                # 查找下一行的中文翻译
                second_part_text = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()

                    # 检查下一行是否是相同序号的中文翻译（带序号）
                    if separator and f"{separator} " in next_line:
                        next_parts = next_line.split(f"{separator} ", 1)
                        next_index_str = next_parts[0].strip()
                        if next_index_str.isdigit() and int(next_index_str) == index:
                            second_part_text = (
                                next_parts[1].strip() if len(next_parts) > 1 else ""
                            )

                    # 如果下一行不是带序号的中文，检查是否是不带序号的中文
                    if not second_part_text and next_line:
                        # 判断是否是另一个序号行
                        is_next_index_line = False
                        if ". " in next_line:
                            potential_index = next_line.split(". ", 1)[0].strip()
                            is_next_index_line = potential_index.isdigit()
                        elif ": " in next_line:
                            potential_index = next_line.split(": ", 1)[0].strip()
                            is_next_index_line = potential_index.isdigit()

                        # 如果不是下一个序号行，且不是注释，则认为是中文翻译
                        if not is_next_index_line and not next_line.startswith("#"):
                            second_part_text = next_line

                    # 根据是否有第二行决定跳过的行数
                    if second_part_text:
                        i += 2  # 跳过两行
                    else:
                        i += 1
                else:
                    i += 1

                # 构建结果文本
                if second_part_text:
                    # 有第二行，组合成双语
                    translated_map[index] = f"{first_part_text}\n{second_part_text}"
                else:
                    # 没有第二行，标记格式可能不正确
                    format_valid = False
                    translated_map[index] = first_part_text
            else:
                i += 1

        return translated_map, format_valid

    def _ensure_translation_completeness(
        self,
        translated_map: Dict[int, str],
        batch_subtitles: List[Dict[str, Any]],
        batch_offset: int = 0,
    ) -> List[str]:
        """确保翻译完整性，返回按序号排序的翻译文本列表

        Args:
            translated_map: 翻译映射字典 {全局序号: 翻译文本}
            batch_subtitles: 当前批次的字幕列表
            batch_offset: 当前批次在整个字幕中的偏移量（用于计算全局序号）

        Returns:
            按序号排序的翻译文本列表，缺失的用原文填充
        """
        translated_texts = []
        for i, sub in enumerate(batch_subtitles):
            # 计算全局序号
            global_seq_num = batch_offset + i + 1
            if global_seq_num in translated_map:
                translated_texts.append(translated_map[global_seq_num])
            else:
                logger.warning(f"翻译缺失第 {global_seq_num} 条，使用原文填充")
                translated_texts.append(sub["text"])

        return translated_texts

    def _rebuild_srt_from_batches(
        self, subtitles: List[Dict[str, Any]], translated_texts: List[str]
    ) -> str:
        """从翻译结果重建 SRT 文件

        支持双语格式：translated_texts 中的每个元素可以包含换行符分隔的英中双语文本
        """
        lines = []

        for i, sub in enumerate(subtitles):
            if i >= len(translated_texts):
                logger.warning(f"翻译文本不足，第 {i + 1} 条使用原文")
                translated_text = sub["text"]
            else:
                translated_text = translated_texts[i]

            lines.append(str(sub["index"]))
            lines.append(f"{sub['start']} --> {sub['end']}")
            lines.append(translated_text)
            lines.append("")

        return "\n".join(lines)

    async def _call_openai_translate(
        self,
        prompt_template: str,
        subtitle_text: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> str:
        """调用OpenAI API进行翻译"""
        return await llm_complete(
            prompt_template,
            subtitle_text,
            api_key,
            model=model,
            base_url=base_url,
            temperature=0.3,
            max_tokens=8192,
            debug_label="模型",
        )

    def extract_plain_text_from_srt(self, srt_path: Path) -> str:
        """从SRT字幕文件中提取纯文本（去除时间轴和序号）

        Args:
            srt_path: SRT字幕文件路径

        Returns:
            提取的纯文本
        """
        try:
            subtitles = self._parse_srt_file(srt_path)

            # 提取所有字幕文本并连接
            text_lines = []
            for sub in subtitles:
                text_lines.append(sub["text"])

            # 用空格连接所有文本
            plain_text = " ".join(text_lines)

            logger.info(f"从字幕文件提取纯文本: {len(plain_text)} 字符")
            return plain_text

        except Exception as e:
            logger.error(f"提取纯文本失败: {str(e)}")
            raise

    async def generate_video_description(
        self,
        subtitle_text: str,
        output_path: Optional[Path] = None,
        subtitle_folder: Optional[Path] = None,
    ) -> Path:
        """使用LLM生成视频简介

        Args:
            subtitle_text: 字幕纯文本内容
            output_path: 输出文件路径，如果为None则自动生成
            subtitle_folder: 字幕文件所在文件夹，用于生成默认输出路径

        Returns:
            生成的视频简介文件路径
        """
        try:
            # 检查OpenAI API密钥
            api_key = settings.openai_api_key
            if not api_key:
                logger.error("未设置OPENAI_API_KEY环境变量")
                raise ValueError("OPENAI_API_KEY未设置")

            # 获取base_url和model
            base_url = settings.openai_base_url
            model = settings.openai_model

            # 读取prompt模板
            prompt_path = self.prompts_dir / "description.md"
            if not prompt_path.exists():
                logger.error(f"Prompt文件不存在: {prompt_path}")
                raise FileNotFoundError(f"Prompt文件不存在: {prompt_path}")

            prompt_template = prompt_path.read_text(encoding="utf-8")

            logger.info("正在调用LLM生成视频简介...")

            # 调用LLM生成简介
            import openai

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            client = openai.AsyncOpenAI(**client_kwargs)

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": subtitle_text},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            # 获取生成的简介
            description = response.choices[0].message.content.strip()

            # 不再在简介开头添加YouTube链接，因为链接已在转载设置(source字段)中
            final_description = description

            # 生成输出路径
            if output_path is None:
                # 优先使用字幕所在文件夹，否则使用默认路径
                if subtitle_folder is not None:
                    output_path = subtitle_folder / "video_description.txt"
                else:
                    output_path = Path("data") / "video_description.txt"

            # 保存简介文件
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(final_description, encoding="utf-8")

            logger.info(f"视频简介已生成: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"生成视频简介失败: {str(e)}")
            raise

    async def generate_description_from_subtitle(
        self, subtitle_path: Path, output_path: Optional[Path] = None
    ) -> Path:
        """从字幕文件生成视频简介的便捷方法

        Args:
            subtitle_path: 中文字幕文件路径
            output_path: 输出文件路径，如果为None则自动生成

        Returns:
            生成的视频简介文件路径
        """
        try:
            logger.info(f"从字幕文件生成视频简介: {subtitle_path.name}")

            # 从字幕提取纯文本
            plain_text = self.extract_plain_text_from_srt(subtitle_path)

            # 生成视频简介（传入字幕文件夹以便保存到正确位置）
            description_path = await self.generate_video_description(
                plain_text, output_path, subtitle_folder=subtitle_path.parent
            )

            logger.info("视频简介生成完成")
            return description_path

        except Exception as e:
            logger.error(f"从字幕生成视频简介失败: {str(e)}")
            raise

    def convert_srt_to_ass(
        self,
        srt_path: Path,
        output_path: Optional[Path] = None,
        en_font_size: int = 16,
        zh_font_size: int = 20,
    ) -> Path:
        """将双语SRT字幕转换为ASS格式，支持中英文字号不同

        Args:
            srt_path: 双语SRT字幕文件路径
            output_path: 输出ASS文件路径，如果为None则自动生成
            en_font_size: 英文字号
            zh_font_size: 中文字号

        Returns:
            ASS字幕文件路径
        """
        try:
            # 生成输出路径（统一为 zh.ass）
            if output_path is None:
                output_path = srt_path.parent / "zh.ass"

            logger.info(f"正在转换SRT到ASS: {srt_path.name}")

            # ASS文件头
            ass_header = f"""[Script Info]
Title: Bilingual Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: English,DejaVu Sans,{en_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,4,1
Style: Chinese,Source Han Sans CN,{zh_font_size},&H00FFFFFF,&H000000FF,&H00503129,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,{en_font_size + 8},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

            # 解析SRT字幕
            subtitles = self._parse_srt_file(srt_path)

            # 转换为ASS格式
            ass_lines = []
            for sub in subtitles:
                # 转换时间格式: 00:00:00,000 -> 0:00:00.00
                start_time = self._srt_time_to_ass_time(sub["start"])
                end_time = self._srt_time_to_ass_time(sub["end"])

                # 处理字幕文本（支持双语）
                text_lines = sub["text"].split("\n")

                # 分离中文和英文行
                chinese_lines = []
                english_lines = []

                for line in text_lines:
                    # 检测是否为中文（包含中文字符）
                    has_chinese = any("\u4e00" <= char <= "\u9fff" for char in line)

                    if has_chinese:
                        # 中文字幕使用 Chinese 样式（圆体、白字蓝色描边）
                        chinese_lines.append(line)
                    else:
                        # 英文字幕使用 English 样式
                        english_lines.append(line)

                # 先输出英文（Layer=0, MarginV=50），再输出中文（Layer=1, MarginV=90）
                # 这样中文会显示在上方，英文在下方
                if english_lines:
                    # 合并所有英文行
                    en_text = "\\N".join(english_lines)
                    ass_lines.append(
                        f"Dialogue: 0,{start_time},{end_time},English,,0,0,0,,{en_text}"
                    )

                if chinese_lines:
                    # 合并所有中文行
                    zh_text = "\\N".join(chinese_lines)
                    ass_lines.append(
                        f"Dialogue: 1,{start_time},{end_time},Chinese,,0,0,0,,{zh_text}"
                    )

            # 写入ASS文件
            ass_content = ass_header + "\n".join(ass_lines)
            output_path.write_text(ass_content, encoding="utf-8-sig")  # UTF-8 with BOM

            logger.info(f"ASS字幕转换完成: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"转换SRT到ASS失败: {str(e)}")
            raise

    def _srt_time_to_ass_time(self, srt_time: str) -> str:
        """将SRT时间格式转换为ASS时间格式

        Args:
            srt_time: SRT时间格式 (00:00:00,000)

        Returns:
            ASS时间格式 (0:00:00.00)
        """
        # 解析SRT时间
        parts = srt_time.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_ms = parts[2].split(",")
        seconds = int(seconds_ms[0])
        milliseconds = int(seconds_ms[1])

        # 转换为ASS时间格式
        # ASS格式: H:MM:SS.CentiSeconds
        centiseconds = milliseconds // 10
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    async def embed_subtitles_to_video(
        self, video_path: Path, subtitle_path: Path, output_path: Optional[Path] = None
    ) -> Path:
        """将字幕嵌入到视频中（硬字幕）

        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径（SRT或ASS格式）
            output_path: 输出视频路径，如果为None则在原视频名后加_embedded

        Returns:
            嵌入字幕后的视频文件路径
        """
        try:
            # 生成输出路径（移除 _original 后缀，得到最终视频名 {title}.mp4）
            if output_path is None:
                # 如果视频名是 {title}_original.mp4，去掉 _original
                stem = video_path.stem
                if stem.endswith("_original"):
                    stem = stem[:-9]  # 去掉 "_original"
                output_path = video_path.parent / f"{stem}.mp4"

            logger.info(
                f"正在将字幕嵌入视频: {video_path.name} + {subtitle_path.name} -> {output_path.name}"
            )

            # 如果是SRT格式，转换为ASS格式以支持不同字号
            if subtitle_path.suffix.lower() == ".srt":
                logger.info("检测到SRT格式字幕，转换为ASS格式以支持双语字号")
                subtitle_path = self.convert_srt_to_ass(
                    subtitle_path, en_font_size=36, zh_font_size=60
                )

            # 创建不含特殊字符的临时字幕文件路径
            # 解决 FFmpeg ass 滤镜无法正确处理路径中特殊字符（如单引号）的问题
            import shutil
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ass", delete=False
            ) as tmp:
                temp_subtitle_path = Path(tmp.name)
            # 复制字幕内容到临时文件
            shutil.copy(subtitle_path, temp_subtitle_path)
            logger.info(f"创建临时字幕文件: {temp_subtitle_path}")
            try:
                # 使用临时文件路径（不含特殊字符）
                subtitle_path_arg = str(temp_subtitle_path)

                # 获取硬件编码器配置
                hwaccel_config = self._get_hwaccel_config()
                encoder = hwaccel_config["encoder"]
                hwaccel_args = hwaccel_config["args"]
                accel_type = hwaccel_config["type"]

                if accel_type != "none":
                    logger.info(f"使用硬件加速: {accel_type} ({encoder})")

                # 构建视频滤镜（VAAPI需要特殊处理）
                if accel_type == "vaapi":
                    # VAAPI需要硬件上传和格式转换
                    video_filter = f"hwupload,format=nv12|vaapi,hwdownload,format=nv12,ass={subtitle_path_arg}"
                else:
                    video_filter = f"ass={subtitle_path_arg}"

                # 构建FFmpeg命令
                cmd = ["ffmpeg"]
                cmd.extend(hwaccel_args)
                cmd.extend(
                    [
                        "-i",
                        str(video_path),
                        "-vf",
                        video_filter,
                        "-c:a",
                        "copy",  # 音频直接复制，不重新编码
                        "-c:v",
                        encoder,
                        "-preset",
                        settings.ffmpeg_preset,
                        "-y",  # 覆盖输出文件
                        str(output_path),
                    ]
                )

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0 and output_path.exists():
                    logger.info(f"字幕嵌入成功: {output_path.name}")
                    return output_path
                else:
                    logger.error(
                        f"字幕嵌入失败: {stderr.decode('utf-8', errors='ignore')}"
                    )
                    raise RuntimeError("FFmpeg字幕嵌入失败")
            finally:
                # 清理临时字幕文件
                if "temp_subtitle_path" in locals() and temp_subtitle_path.exists():
                    temp_subtitle_path.unlink()
                    logger.info(f"已删除临时字幕文件: {temp_subtitle_path.name}")

        except FileNotFoundError:
            logger.error("未找到FFmpeg，请确保已安装FFmpeg并添加到PATH环境变量")
            raise
        except Exception as e:
            logger.error(f"字幕嵌入异常: {str(e)}")
            raise

    def _get_hwaccel_config(self) -> dict:
        """获取硬件加速配置

        Returns:
            包含编码器、硬件加速参数和类型的字典
        """
        hwaccel = settings.ffmpeg_hwaccel.lower()

        # 如果设置为none，使用软件编码
        if hwaccel == "none":
            return {"encoder": "libx264", "args": [], "type": "none"}

        # 如果指定了特定硬件加速器
        if hwaccel != "auto":
            return self._get_specific_encoder(hwaccel)

        # 自动检测可用的硬件加速器
        return self._detect_hwaccel()

    def _get_specific_encoder(self, hwaccel: str) -> dict:
        """获取指定的硬件编码器配置

        Args:
            hwaccel: 硬件加速类型 (nvenc, qsv, amf, videotoolbox, vaapi)

        Returns:
            包含编码器、硬件加速参数和类型的字典
        """
        configs = {
            "nvenc": {"encoder": "h264_nvenc", "args": [], "type": "nvenc"},
            "qsv": {
                "encoder": "h264_qsv",
                "args": ["-init_hw_device", "qsv=qsv", "-filter_hw_device", "qsv"],
                "type": "qsv",
            },
            "amf": {"encoder": "h264_amf", "args": [], "type": "amf"},
            "videotoolbox": {
                "encoder": "h264_videotoolbox",
                "args": [],
                "type": "videotoolbox",
            },
            "vaapi": {
                "encoder": "h264_vaapi",
                "args": ["-vaapi_device", "/dev/dri/renderD128"],
                "type": "vaapi",
            },
        }

        if hwaccel in configs:
            return configs[hwaccel]

        # 如果指定了无效的加速器，回退到软件编码
        logger.warning(f"未知的硬件加速类型: {hwaccel}，使用软件编码")
        return {"encoder": "libx264", "args": [], "type": "none"}

    def _detect_hwaccel(self) -> dict:
        """自动检测可用的硬件加速器

        Returns:
            包含编码器、硬件加速参数和类型的字典
        """
        import subprocess

        # 检测优先级：nvenc > qsv > amf > videotoolbox > vaapi
        detection_order = [
            ("nvenc", ["ffmpeg", "-hide_banner", "-encoders"]),
            ("qsv", ["ffmpeg", "-hide_banner", "-encoders"]),
            ("amf", ["ffmpeg", "-hide_banner", "-encoders"]),
            ("videotoolbox", ["ffmpeg", "-hide_banner", "-encoders"]),
            ("vaapi", ["ffmpeg", "-hide_banner", "-encoders"]),
        ]

        encoder_names = {
            "nvenc": "h264_nvenc",
            "qsv": "h264_qsv",
            "amf": "h264_amf",
            "videotoolbox": "h264_videotoolbox",
            "vaapi": "h264_vaapi",
        }

        for accel_type, cmd in detection_order:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if encoder_names[accel_type] in result.stdout:
                    logger.info(f"检测到硬件加速器: {accel_type}")
                    return self._get_specific_encoder(accel_type)
            except (
                subprocess.TimeoutExpired,
                FileNotFoundError,
                subprocess.CalledProcessError,
                OSError,
            ):
                continue

        # 未检测到任何硬件加速器，使用软件编码
        logger.info("未检测到可用的硬件加速器，使用软件编码 (libx264)")
        return {"encoder": "libx264", "args": [], "type": "none"}

    def _get_subtitle_cache_path(self, output_path: Path) -> Path:
        """获取字幕翻译缓存文件路径

        Args:
            output_path: 输出字幕文件路径

        Returns:
            缓存文件路径
        """
        return output_path.parent / f"{output_path.stem}.cache.json"

    def _calculate_subtitle_hash(self, subtitle_path: Path) -> str:
        """计算字幕文件的哈希值，用于验证缓存有效性

        Args:
            subtitle_path: 字幕文件路径

        Returns:
            MD5哈希值
        """
        content = subtitle_path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _load_translation_cache(
        self, cache_path: Path, expected_hash: str, expected_total: int, batch_size: int
    ) -> Optional[Dict[str, Any]]:
        """加载翻译缓存

        Args:
            cache_path: 缓存文件路径
            expected_hash: 预期的字幕哈希值
            expected_total: 预期的字幕总数
            batch_size: 批次大小

        Returns:
            缓存数据字典，如果缓存无效则返回 None
        """
        try:
            if not cache_path.exists():
                logger.info("未找到翻译缓存文件")
                return None

            logger.info(f"找到翻译缓存文件: {cache_path.name}")
            cache_data = json.loads(cache_path.read_text(encoding="utf-8"))

            # 验证缓存是否有效
            if cache_data.get("subtitle_hash") != expected_hash:
                logger.warning("字幕文件已更改，缓存无效")
                return None

            if cache_data.get("total_subtitles") != expected_total:
                logger.warning("字幕数量不匹配，缓存无效")
                return None

            if cache_data.get("batch_size") != batch_size:
                logger.warning("批次大小不匹配，缓存无效")
                return None

            translated_batches = cache_data.get("translated_batches", {})
            cached_count = len(translated_batches) * batch_size
            logger.info(
                f"缓存有效: 已翻译 {cached_count}/{expected_total} 条字幕 ({len(translated_batches)} 批)"
            )

            return cache_data

        except Exception as e:
            logger.error(f"加载缓存文件失败: {str(e)}")
            return None

    def _save_translation_cache(
        self,
        cache_path: Path,
        subtitle_hash: str,
        total_subtitles: int,
        batch_size: int,
        translated_batches: Dict[int, List[str]],
    ) -> None:
        """保存翻译缓存

        Args:
            cache_path: 缓存文件路径
            subtitle_hash: 字幕文件哈希值
            total_subtitles: 字幕总数
            batch_size: 批次大小
            translated_batches: 已翻译的批次数据 {批次索引: [翻译文本列表]}
        """
        try:
            cache_data = {
                "subtitle_hash": subtitle_hash,
                "total_subtitles": total_subtitles,
                "batch_size": batch_size,
                "translated_batches": {
                    str(k): v for k, v in translated_batches.items()
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            cache_path.write_text(
                json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.debug(f"翻译缓存已保存: {cache_path.name}")

        except Exception as e:
            logger.error(f"保存缓存文件失败: {str(e)}")

    def _update_translation_cache(
        self,
        cache_path: Path,
        cache_data: Dict[str, Any],
        batch_index: int,
        translated_texts: List[str],
    ) -> None:
        """更新翻译缓存（添加一个新批次）

        Args:
            cache_path: 缓存文件路径
            cache_data: 现有缓存数据
            batch_index: 批次索引
            translated_texts: 该批次的翻译文本列表
        """
        try:
            # 更新批次数据
            translated_batches = cache_data.get("translated_batches", {})
            translated_batches[str(batch_index)] = translated_texts
            cache_data["translated_batches"] = translated_batches
            cache_data["updated_at"] = datetime.now().isoformat()

            # 保存更新后的缓存
            cache_path.write_text(
                json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.debug(f"缓存已更新: 批次 {batch_index}")

        except Exception as e:
            logger.error(f"更新缓存文件失败: {str(e)}")

    def _clear_translation_cache(self, cache_path: Path) -> None:
        """清除翻译缓存文件

        Args:
            cache_path: 缓存文件路径
        """
        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"翻译缓存已清除: {cache_path.name}")
        except Exception as e:
            logger.error(f"清除缓存文件失败: {str(e)}")
