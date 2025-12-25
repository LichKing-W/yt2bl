"""字幕处理模块"""

import asyncio
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
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
                    "start_time": match[1],
                    "end_time": match[2],
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

            # 读取原始字幕文件内容
            subtitle_content = subtitle_path.read_text(encoding="utf-8")

            # 生成输出路径
            if output_path is None:
                output_path = subtitle_path.parent / f"{subtitle_path.stem}_zh.srt"

            logger.info(f"正在翻译字幕，共 {len(subtitle_content)} 字符")

            try:
                # 调用OpenAI API - 一次性翻译整个字幕文件
                translated_content = await self._call_openai_translate(
                    prompt_template, subtitle_content, api_key, base_url, model
                )

                # 直接保存翻译结果
                output_path.write_text(translated_content, encoding="utf-8")

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

    def _format_subtitles_for_translation(self, subtitles: List[Dict[str, Any]]) -> str:
        """格式化字幕用于翻译"""
        lines = []
        for sub in subtitles:
            lines.append(f"{sub['index']}: {sub['text']}")
        return "\n".join(lines)

    async def _call_openai_translate(
        self, prompt_template: str, subtitle_text: str, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o-mini"
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
                    {"role": "user", "content": subtitle_text}
                ],
                temperature=0.3,
                max_tokens=16384,  # 增加token限制以支持完整字幕文件
            )

            # 获取翻译结果
            translated_text = response.choices[0].message.content.strip()
            return translated_text

        except ImportError:
            logger.error("未安装openai库，请运行: pip install openai")
            raise
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise

    def _parse_translated_result(self, translated_text: str, expected_count: int) -> List[str]:
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
                if line.startswith("#") or line.startswith("以下是") or line.startswith("翻译"):
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
                    line.strip() for line in lines
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
                lines.append(f"{sub['start_time']} --> {sub['end_time']}")
                lines.append(translated_texts[i])
            else:
                # 翻译数量不足时使用原文
                lines.append(f"{sub['index']}")
                lines.append(f"{sub['start_time']} --> {sub['end_time']}")
                lines.append(sub['text'])
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def merge_bilingual_srt(self, original_srt_path: Path, translated_srt_path: Path, output_path: Optional[Path] = None) -> Path:
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
                output_path = original_srt_path.parent / f"{original_srt_path.stem}_bilingual.srt"

            logger.info(f"正在合并双语字幕: {original_srt_path.name} + {translated_srt_path.name}")

            # 解析原始字幕
            original_subs = self._parse_srt_file(original_srt_path)
            # 解析翻译字幕
            translated_subs = self._parse_srt_file(translated_srt_path)

            # 合并字幕
            merged_lines = []
            for orig_sub in original_subs:
                index = orig_sub['index']
                start_time = orig_sub['start_time']
                end_time = orig_sub['end_time']
                original_text = orig_sub['text']

                # 查找对应的翻译
                translated_text = ""
                for trans_sub in translated_subs:
                    if trans_sub['index'] == index:
                        translated_text = trans_sub['text']
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

    def _parse_srt_file(self, srt_path: Path) -> List[Dict[str, Any]]:
        """解析SRT字幕文件

        Args:
            srt_path: SRT文件路径

        Returns:
            字幕条目列表，每个条目包含 index, start_time, end_time, text
        """
        subtitles = []
        content = srt_path.read_text(encoding="utf-8")

        # 按空行分割字幕块
        blocks = re.split(r'\n\s*\n', content.strip())

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    index = int(lines[0].strip())
                    time_line = lines[1].strip()
                    text_lines = lines[2:]

                    # 解析时间轴
                    time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', time_line)
                    if time_match:
                        start_time = time_match.group(1)
                        end_time = time_match.group(2)
                        text = '\n'.join(text_lines)

                        subtitles.append({
                            'index': index,
                            'start_time': start_time,
                            'end_time': end_time,
                            'text': text
                        })
                except (ValueError, IndexError) as e:
                    logger.debug(f"跳过无法解析的字幕块: {block[:50]}...")
                    continue

        return subtitles

    def convert_srt_to_ass(self, srt_path: Path, output_path: Optional[Path] = None, en_font_size: int = 16, zh_font_size: int = 20) -> Path:
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
            # 生成输出路径
            if output_path is None:
                output_path = srt_path.parent / f"{srt_path.stem}.ass"

            logger.info(f"正在转换SRT到ASS: {srt_path.name}")

            # ASS文件头
            ass_header = """[Script Info]
Title: Bilingual Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1280
PlayResY: 720
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

            # 解析SRT字幕
            subtitles = self._parse_srt_file(srt_path)

            # 转换为ASS格式
            ass_lines = []
            for sub in subtitles:
                # 转换时间格式: 00:00:00,000 -> 0:00:00.00
                start_time = self._srt_time_to_ass_time(sub['start_time'])
                end_time = self._srt_time_to_ass_time(sub['end_time'])

                # 处理字幕文本（支持双语）
                text_lines = sub['text'].split('\n')

                # 分离中文和英文行
                chinese_lines = []
                english_lines = []

                for line in text_lines:
                    # 检测是否为中文（包含中文字符）
                    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in line)

                    if has_chinese:
                        # 中文字幕使用较大字号
                        chinese_lines.append(f"{{\\fs{zh_font_size}}}{line}")
                    else:
                        # 英文字幕使用较小字号
                        english_lines.append(f"{{\\fs{en_font_size}}}{line}")

                # 构建ASS格式的文本：中文在上，英文在下
                ass_text_parts = []
                if chinese_lines:
                    ass_text_parts.extend(chinese_lines)
                if english_lines:
                    ass_text_parts.extend(english_lines)

                # 合并多行，使用\\N换行
                ass_text = "\\N".join(ass_text_parts)

                ass_lines.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{ass_text}")

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
        parts = srt_time.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_ms = parts[2].split(',')
        seconds = int(seconds_ms[0])
        milliseconds = int(seconds_ms[1])

        # 转换为ASS时间格式
        # ASS格式: H:MM:SS.CentiSeconds
        centiseconds = milliseconds // 10
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    async def embed_subtitles_to_video(self, video_path: Path, subtitle_path: Path, output_path: Optional[Path] = None) -> Path:
        """将字幕嵌入到视频中（硬字幕）

        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径（SRT或ASS格式）
            output_path: 输出视频路径，如果为None则在原视频名后加_embedded

        Returns:
            嵌入字幕后的视频文件路径
        """
        try:
            # 生成输出路径
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_embedded{video_path.suffix}"

            logger.info(f"正在将字幕嵌入视频: {video_path.name} + {subtitle_path.name}")

            # 如果是SRT格式，转换为ASS格式以支持不同字号
            if subtitle_path.suffix.lower() == '.srt':
                logger.info("检测到SRT格式字幕，转换为ASS格式以支持双语字号")
                subtitle_path = self.convert_srt_to_ass(subtitle_path, en_font_size=13, zh_font_size=17)

            # 使用FFmpeg嵌入字幕（ASS格式）
            # 需要转义路径中的特殊字符
            escaped_subtitle_path = str(subtitle_path).replace('\\', '\\\\\\\\').replace(':', '\\\\:')

            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-vf", f"ass='{escaped_subtitle_path}'",
                "-c:a", "copy",  # 音频直接复制，不重新编码
                "-y",  # 覆盖输出文件
                str(output_path)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
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
