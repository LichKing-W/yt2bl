"""字幕处理模块"""

import asyncio
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import tempfile
import json

from ..utils.logger import logger
from ..utils.config import settings


class SubtitleProcessor:
    """字幕处理器"""

    def __init__(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / "youtube_to_bilibili_subtitles"
        self.temp_dir.mkdir(exist_ok=True)
        # 项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        self.prompts_dir = self.project_root / "prompts"

    async def extract_subtitles(self, video_path: Path) -> Optional[Path]:
        """提取视频字幕"""
        try:
            logger.info(f"开始提取字幕: {video_path}")

            subtitle_path = self.temp_dir / f"subtitles_{video_path.stem}.srt"

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-map",
                "0:s:0",  # 提取第一个字幕流
                "-c:s",
                "srt",
                "-y",  # 覆盖输出文件
                str(subtitle_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and subtitle_path.exists():
                logger.info(f"字幕提取成功: {subtitle_path}")
                return subtitle_path
            else:
                logger.warning(f"字幕提取失败或无字幕: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"字幕提取异常: {str(e)}")
            return None

    async def translate_subtitles(
        self, subtitle_path: Path, target_lang: str = "zh-CN"
    ) -> Optional[Path]:
        """翻译字幕（简化版本，实际需要翻译API）"""
        try:
            logger.info(f"开始翻译字幕: {subtitle_path} -> {target_lang}")

            # 这里只是示例，实际翻译需要调用翻译API
            # 如百度翻译、谷歌翻译或ChatGPT API

            translated_path = (
                self.temp_dir / f"translated_{subtitle_path.stem}_{target_lang}.srt"
            )

            # 读取原字幕
            content = subtitle_path.read_text(encoding="utf-8")

            # 简单的字幕格式处理示例
            translated_content = await self._simple_translate(content, target_lang)

            translated_path.write_text(translated_content, encoding="utf-8")

            logger.info(f"字幕翻译完成: {translated_path}")
            return translated_path

        except Exception as e:
            logger.error(f"字幕翻译异常: {str(e)}")
            return None

    async def _simple_translate(self, content: str, target_lang: str) -> str:
        """简单翻译示例（实际需要集成翻译服务）"""
        # 这里只是一个占位符，实际应该调用翻译API
        # 返回原内容，仅作为示例

        if target_lang.startswith("zh"):
            # 可以在这里添加一些简单的英文到中文的映射
            replacements = {
                "Hello": "你好",
                "Welcome": "欢迎",
                "Thank you": "谢谢",
                "Goodbye": "再见",
                "Tutorial": "教程",
                "Programming": "编程",
                "Code": "代码",
                "Function": "函数",
                "Variable": "变量",
                "Algorithm": "算法",
                "Data Structure": "数据结构",
            }

            for en, zh in replacements.items():
                content = re.sub(
                    r"\b" + re.escape(en) + r"\b", zh, content, flags=re.IGNORECASE
                )

        return content

    async def convert_subtitle_format(
        self, subtitle_path: Path, target_format: str = "ass"
    ) -> Optional[Path]:
        """转换字幕格式"""
        try:
            logger.info(f"开始转换字幕格式: {subtitle_path} -> {target_format}")

            output_path = (
                self.temp_dir / f"converted_{subtitle_path.stem}.{target_format}"
            )

            cmd = [
                "ffmpeg",
                "-i",
                str(subtitle_path),
                "-c:s",
                target_format,
                "-y",  # 覆盖输出文件
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and output_path.exists():
                logger.info(f"字幕格式转换完成: {output_path}")
                return output_path
            else:
                logger.error(f"字幕格式转换失败: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"字幕格式转换异常: {str(e)}")
            return None

    async def embed_subtitles_to_video(
        self, video_path: Path, subtitle_path: Path
    ) -> Optional[Path]:
        """将字幕嵌入视频"""
        try:
            logger.info(f"开始嵌入字幕到视频: {video_path}")

            output_path = self.temp_dir / f"with_subs_{video_path.stem}.mp4"

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-i",
                str(subtitle_path),
                "-c",
                "copy",
                "-c:s",
                "mov_text",  # 使用mov_text编码器
                "-metadata:s:s:0",
                "language=chi",  # 设置字幕语言为中文
                "-disposition:s:0",
                "default",  # 设置为默认字幕
                "-y",  # 覆盖输出文件
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and output_path.exists():
                logger.info(f"字幕嵌入完成: {output_path}")
                return output_path
            else:
                logger.error(f"字幕嵌入失败: {stderr.decode('utf-8')}")
                return None

        except Exception as e:
            logger.error(f"字幕嵌入异常: {str(e)}")
            return None

    async def parse_srt_subtitle(self, subtitle_path: Path) -> List[Dict[str, Any]]:
        """解析SRT字幕文件"""
        try:
            content = subtitle_path.read_text(encoding="utf-8")
            subtitles = []

            # SRT格式解析
            pattern = r"(\d+)\s*\n([\d:,]+)\s*-->\s*([\d:,]+)\s*\n(.+?)(?=\n\d+|\Z)"
            matches = re.findall(pattern, content, re.DOTALL)

            for match in matches:
                subtitle_entry = {
                    "index": int(match[0]),
                    "start": match[1],
                    "end": match[2],
                    "text": match[3].strip().replace("\n", " "),
                }
                subtitles.append(subtitle_entry)

            logger.info(f"解析字幕文件: {len(subtitles)} 条字幕")
            return subtitles

        except Exception as e:
            logger.error(f"解析字幕文件失败: {str(e)}")
            return []

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
        - 如果第一行中文字符>20，则不合并，作为单独一行

        Args:
            srt_path: SRT字幕文件路径

        Returns:
            合并后的字幕文件路径
        """
        try:
            logger.info(f"正在合并字幕行: {srt_path.name}")

            # 解析字幕
            subtitles = self._parse_srt_file(srt_path)

            # 每两行合并为一行，但检查中文字符数
            merged_subtitles = []
            i = 0
            while i < len(subtitles):
                if i + 1 < len(subtitles):
                    # 有两行，检查是否应该合并
                    sub1 = subtitles[i]
                    sub2 = subtitles[i + 1]

                    # 计算第一行的中文字符数
                    zh_char_count = self._count_chinese_characters(sub1["text"])

                    if zh_char_count > 20:
                        # 第一行中文字符过多，不合并
                        logger.debug(
                            f"第一行中文字符过多({zh_char_count}个)，不合并字幕{i + 1}"
                        )
                        merged_sub = {
                            "index": len(merged_subtitles) + 1,
                            "start": sub1["start"],
                            "end": sub1["end"],
                            "text": sub1["text"],
                        }
                        merged_subtitles.append(merged_sub)
                        i += 1
                    else:
                        # 正常合并两行
                        merged_sub = {
                            "index": len(merged_subtitles) + 1,
                            "start": sub1["start"],
                            "end": sub2["end"],
                            "text": f"{sub1['text']} {sub2['text']}",
                        }
                        merged_subtitles.append(merged_sub)
                        logger.debug(
                            f"合并: 字幕{i + 1}和{i + 2} -> 字幕{len(merged_subtitles)}"
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

    def _count_chinese_characters(self, text: str) -> int:
        """计算文本中的中文字符数量

        Args:
            text: 待统计的文本

        Returns:
            中文字符数量
        """
        count = 0
        for char in text:
            # 判断是否为中文字符（Unicode 范围）
            if "\u4e00" <= char <= "\u9fff":
                count += 1
        return count

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
            logger.info(
                f"步骤 3/4: 正在分批翻译字幕，共 {total_subtitles} 条，分 {total_batches} 批"
            )

            try:
                for i in range(0, total_subtitles, batch_size):
                    batch_num = i // batch_size + 1
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
                logger.info(f"步骤 4/4: 重建字幕文件...")
                final_content = self._rebuild_srt_from_batches(
                    subtitles, all_translated_texts
                )

                # 保存翻译结果
                output_path.write_text(final_content, encoding="utf-8")

                # 删除临时的预处理文件
                merged_subtitle_path.unlink()

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
        """格式化字幕批次用于翻译"""
        lines = []
        for i, sub in enumerate(subtitles):
            seq_num = offset + i + 1
            lines.append(f"{seq_num}: {sub['text']}")
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

    def _format_subtitles_for_translation(self, subtitles: List[Dict[str, Any]]) -> str:
        """格式化字幕用于翻译"""
        lines = []
        for sub in subtitles:
            lines.append(f"{sub['index']}: {sub['text']}")
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
        try:
            import openai

            # 构建客户端参数
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
                logger.info(f"使用自定义API端点: {base_url}")

            client = openai.AsyncOpenAI(**client_kwargs)

            # 调用API - prompt_template作为system，subtitle_text作为user
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": subtitle_text},
                ],
                temperature=0.3,
                max_tokens=8192,  # 增加token限制以支持完整字幕文件
            )
            logger.info(response)

            # 获取翻译结果
            translated_text = response.choices[0].message.content.strip()

            # 记录模型原始输出（用于调试）
            logger.debug(f"[模型原始输出]\n{translated_text}\n[/模型原始输出]")

            return translated_text

        except ImportError:
            logger.error("未安装openai库，请运行: pip install openai")
            raise
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise

    def _parse_translated_result(
        self, translated_text: str, expected_count: int
    ) -> List[str]:
        """解析翻译结果，提取翻译后的文本"""
        try:
            # 尝试按行分割
            lines = translated_text.split("\n")

            # 过滤掉空行和说明性文本
            translated_entries = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 跳过说明性文字
                if (
                    line.startswith("#")
                    or line.startswith("以下是")
                    or line.startswith("翻译")
                ):
                    continue

                # 提取序号后的文本（格式如 "1: 翻译文本"）
                if ":" in line and line[0].isdigit():
                    # 找到第一个冒号后的文本
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        translated_entries.append(parts[1].strip())
                    else:
                        translated_entries.append(line)
                else:
                    translated_entries.append(line)

            # 如果数量不足，返回所有非空行
            if len(translated_entries) < expected_count:
                # 重新解析，直接使用所有非空行
                translated_entries = [
                    line.strip()
                    for line in lines
                    if line.strip() and not line.startswith("#")
                ]

            return translated_entries[:expected_count]

        except Exception as e:
            logger.debug(f"解析翻译结果失败: {str(e)}")
            return []

    def _rebuild_srt(
        self, original_subtitles: List[Dict[str, Any]], translated_texts: List[str]
    ) -> str:
        """重建SRT字幕文件"""
        lines = []

        for i, sub in enumerate(original_subtitles):
            if i < len(translated_texts):
                lines.append(f"{sub['index']}")
                lines.append(f"{sub['start']} --> {sub['end']}")
                lines.append(translated_texts[i])
            else:
                # 翻译数量不足时使用原文
                lines.append(f"{sub['index']}")
                lines.append(f"{sub['start']} --> {sub['end']}")
                lines.append(sub["text"])
            lines.append("")  # 空行分隔

        return "\n".join(lines)

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

            logger.info(f"视频简介生成完成")
            return description_path

        except Exception as e:
            logger.error(f"从字幕生成视频简介失败: {str(e)}")
            raise

    def merge_bilingual_srt(
        self,
        original_srt_path: Path,
        translated_srt_path: Path,
        output_path: Optional[Path] = None,
    ) -> Path:
        """合并中英双语字幕文件

        Args:
            original_srt_path: 原始英文字幕文件路径
            translated_srt_path: 翻译后的中文字幕文件路径
            output_path: 输出文件路径，如果为None则自动生成

        Returns:
            合并后的双语字幕文件路径
        """
        try:
            # 生成输出路径
            if output_path is None:
                output_path = (
                    original_srt_path.parent / f"{original_srt_path.stem}_bilingual.srt"
                )

            logger.info(
                f"正在合并双语字幕: {original_srt_path.name} + {translated_srt_path.name}"
            )

            # 解析原始字幕
            original_subs = self._parse_srt_file(original_srt_path)
            # 解析翻译字幕
            translated_subs = self._parse_srt_file(translated_srt_path)

            # 合并字幕
            merged_lines = []
            for orig_sub in original_subs:
                index = orig_sub["index"]
                start_time = orig_sub["start"]
                end_time = orig_sub["end"]
                original_text = orig_sub["text"]

                # 查找对应的翻译
                translated_text = ""
                for trans_sub in translated_subs:
                    if trans_sub["index"] == index:
                        translated_text = trans_sub["text"]
                        break

                # 写入双语字幕
                merged_lines.append(str(index))
                merged_lines.append(f"{start_time} --> {end_time}")
                merged_lines.append(original_text)  # 英文
                if translated_text:
                    merged_lines.append(translated_text)  # 中文
                merged_lines.append("")  # 空行分隔

            # 写入合并后的字幕文件
            output_path.write_text("\n".join(merged_lines), encoding="utf-8")
            logger.info(f"双语字幕合并完成: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"合并双语字幕失败: {str(e)}")
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
Style: English,DejaVu Sans,{en_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,0,1
Style: Chinese,Source Han Sans SC,{zh_font_size},&H00FFFFFF,&H000000FF,&H00503129,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,{en_font_size + 4},1

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
                    subtitle_path, en_font_size=32, zh_font_size=56
                )

            # 使用FFmpeg嵌入字幕（ASS格式）
            # 需要转义路径中的特殊字符
            escaped_subtitle_path = (
                str(subtitle_path).replace("\\", "\\\\\\\\").replace(":", "\\\\:")
            )

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vf",
                f"ass='{escaped_subtitle_path}'",
                "-c:a",
                "copy",  # 音频直接复制，不重新编码
                "-y",  # 覆盖输出文件
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and output_path.exists():
                logger.info(f"字幕嵌入成功: {output_path.name}")
                return output_path
            else:
                logger.error(f"字幕嵌入失败: {stderr.decode('utf-8', errors='ignore')}")
                raise RuntimeError("FFmpeg字幕嵌入失败")

        except FileNotFoundError:
            logger.error("未找到FFmpeg，请确保已安装FFmpeg并添加到PATH环境变量")
            raise
        except Exception as e:
            logger.error(f"字幕嵌入异常: {str(e)}")
            raise
