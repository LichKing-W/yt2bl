"""B站内容优化模块"""

import re
from pathlib import Path
from typing import List, Optional

from ..utils.config import settings
from ..utils.llm_client import llm_complete
from ..utils.logger import logger
from ..youtube.models import YouTubeVideo
from .models import BilibiliVideo


class BilibiliContentOptimizer:
    """B站内容优化器"""

    def __init__(self) -> None:
        # B站热门标签列表
        self.hot_tags = [
            "编程",
            "教程",
            "学习",
            "技术",
            "计算机",
            "程序员",
            "软件开发",
            "算法",
            "数据结构",
            "人工智能",
            "机器学习",
            "深度学习",
            "前端",
            "后端",
            "全栈",
            "数据库",
            "Python",
            "JavaScript",
            "Java",
            "C++",
            "Web开发",
            "移动开发",
            "游戏开发",
            "网络安全",
            "云计算",
            "大数据",
            "分享",
            "干货",
            "入门",
            "进阶",
            "项目实战",
            "面试",
            "求职",
        ]

    async def optimize_for_bilibili(
        self, youtube_video: YouTubeVideo, video_path: str
    ) -> BilibiliVideo:
        """将YouTube视频优化为B站格式"""
        try:
            logger.info(f"开始优化视频内容: {youtube_video.title}")

            # 获取视频文件夹路径
            video_path_obj = Path(video_path)
            video_folder = video_path_obj.parent

            # 从文件夹名称中提取YouTuber名称
            # 文件夹格式: {YouTuber名}|{video_id}
            youtuber_name = self._extract_youtuber_name_from_folder(video_folder)

            # 查找封面图
            cover_path = self._find_cover_image(video_folder, video_path_obj.stem)
            if cover_path:
                logger.info(f"找到封面图: {cover_path.name}")
            else:
                logger.info("未找到封面图")

            # 查找并读取生成的视频简介
            description = self._load_video_description(video_folder)
            if description:
                logger.info("使用生成的视频简介")
            else:
                # 如果没有找到简介文件，使用默认优化描述
                description = self.optimize_description(youtube_video)
                logger.info("使用默认描述")

            # 使用LLM生成中文标题
            optimized_title = await self.generate_optimized_title(
                youtube_video.title, youtuber_name, description
            )

            # 生成标签（包含YouTuber名称，使用LLM生成）
            optimized_tags = await self.generate_tags(
                youtube_video, youtuber_name, description
            )

            # 确定分类
            category_id = self.determine_category(youtube_video)

            # 创建B站视频对象
            bilibili_video = BilibiliVideo(
                title=optimized_title,
                description=description,
                tags=optimized_tags,
                category_id=category_id,
                cover_path=str(cover_path) if cover_path else None,
                video_path=video_path,
                copyright=2,  # 转载
                source=youtube_video.url,  # YouTube原视频链接
                repost_desc=self.generate_repost_description(youtube_video),
                dynamic=self.generate_dynamic_content(youtube_video),
            )

            logger.info(f"内容优化完成: {optimized_title}")
            return bilibili_video

        except Exception as e:
            logger.error(f"内容优化失败: {str(e)}")
            # 返回基本的B站视频对象
            return BilibiliVideo(
                title=youtube_video.title,
                description=youtube_video.description,
                video_path=video_path,
                copyright=2,  # 转载
                source=youtube_video.url,  # YouTube原视频链接
            )

    def _find_cover_image(self, video_folder: Path, video_stem: str) -> Optional[Path]:
        """查找视频封面图（优先使用cover.jpg）

        Args:
            video_folder: 视频所在文件夹
            video_stem: 视频文件名（不含扩展名）

        Returns:
            找到的封面图路径，未找到返回None
        """
        try:
            # 优先查找 cover.jpg（标准命名）
            cover_jpg = video_folder / "cover.jpg"
            if cover_jpg.exists():
                return cover_jpg

            # 兼容旧格式：查找与视频同名的封面图
            cover_extensions = [".jpg", ".jpeg", ".png", ".webp"]

            for ext in cover_extensions:
                cover_file = video_folder / f"{video_stem}{ext}"
                if cover_file.exists():
                    return cover_file

            # 如果没找到，查找文件夹中任何图片文件
            for ext in cover_extensions:
                matches = list(video_folder.glob(f"*{ext}"))
                if matches:
                    # 按文件名排序，返回第一个
                    matches.sort(key=lambda x: x.name)
                    return matches[0]

            return None

        except Exception as e:
            logger.debug(f"查找封面图失败: {str(e)}")
            return None

    def _extract_youtuber_name_from_folder(self, video_folder: Path) -> Optional[str]:
        """从文件夹名称中提取YouTuber名称

        Args:
            video_folder: 视频所在文件夹

        Returns:
            YouTuber名称，未找到返回None
        """
        try:
            # 文件夹格式: {YouTuber名}|{video_id}
            folder_name = video_folder.name

            # 查找竖线分隔符（video_id前）
            last_separator = folder_name.rfind("|")
            if last_separator > 0:
                # 提取YouTuber名称（竖线之前的部分）
                youtuber_name = folder_name[:last_separator]
                # 将下划线替换回空格（如果有）
                youtuber_name = youtuber_name.replace("_", " ")
                logger.info(f"从文件夹名提取YouTuber: {youtuber_name}")
                return youtuber_name

            return None

        except Exception as e:
            logger.debug(f"提取YouTuber名称失败: {str(e)}")
            return None

    def _load_video_description(self, video_folder: Path) -> Optional[str]:
        """加载生成的视频简介文件

        Args:
            video_folder: 视频所在文件夹

        Returns:
            视频简介内容，未找到返回None
        """
        try:
            description_file = video_folder / "video_description.txt"
            if description_file.exists():
                content = description_file.read_text(encoding="utf-8")
                logger.info(f"读取视频简介文件: {description_file.name}")
                return content.strip()

            return None

        except Exception as e:
            logger.debug(f"读取视频简介文件失败: {str(e)}")
            return None

    def optimize_title(
        self, original_title: str, youtuber_name: Optional[str] = None
    ) -> str:
        """优化标题

        Args:
            original_title: YouTube原始标题
            youtuber_name: YouTuber名称（从文件夹名提取）

        Returns:
            优化后的标题，格式为 "原标题 | YouTuber名"
        """
        try:
            # 清理标题
            title = original_title.strip()

            # 移除一些不适合B站的符号
            title = re.sub(r"[|]{2,}", "｜", title)
            title = re.sub(r"\s+", " ", title)

            # 如果提供了YouTuber名称，添加到标题末尾
            if youtuber_name:
                title = f"{title} | {youtuber_name}"

            # 检查标题长度
            if len(title) > 80:  # B站标题限制
                # 尝试缩短标题（保留YouTuber名称）
                if youtuber_name:
                    suffix = f" | {youtuber_name}"
                    available_length = 80 - len(suffix)
                    if available_length > 10:
                        title = title[: available_length - 3] + "..." + suffix
                    else:
                        # 如果原标题太长，只能截断
                        title = title[:77] + "..."
                else:
                    title = title[:77] + "..."

            return title

        except Exception:
            return original_title

    async def generate_optimized_title(
        self,
        original_title: str,
        youtuber_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """使用LLM生成优化的中文标题

        Args:
            original_title: YouTube原始标题
            youtuber_name: YouTuber名称
            description: 视频简介内容

        Returns:
            优化后的中文标题，格式为 "中文标题 | YouTuber名"
        """
        try:
            # 如果有简介，使用LLM生成中文标题
            if description:
                try:
                    chinese_title = await self.generate_title_with_llm(
                        original_title, description
                    )
                    if chinese_title:
                        # 添加YouTuber名称
                        if youtuber_name:
                            return f"{chinese_title} | {youtuber_name}"
                        return chinese_title
                except Exception as e:
                    logger.warning(f"LLM标题生成失败，使用原标题: {str(e)}")

            # 回退到原标题优化
            return self.optimize_title(original_title, youtuber_name)

        except Exception:
            return self.optimize_title(original_title, youtuber_name)

    async def generate_title_with_llm(
        self, original_title: str, video_description: str
    ) -> Optional[str]:
        """使用LLM根据原始标题和视频简介生成中文标题

        Args:
            original_title: YouTube原始标题
            video_description: 视频简介内容

        Returns:
            生成的中文标题，失败返回None
        """
        try:
            # 检查API密钥
            api_key = settings.openai_api_key
            if not api_key:
                logger.warning("未设置OPENAI_API_KEY，跳过LLM标题生成")
                return None

            # 获取base_url（可选）
            base_url = settings.openai_base_url

            # 获取模型配置
            model = settings.openai_model

            # 读取prompt模板
            project_root = Path(__file__).parent.parent.parent
            prompt_path = project_root / "prompts" / "generate_title.md"
            if not prompt_path.exists():
                logger.error(f"Prompt文件不存在: {prompt_path}")
                return None

            prompt_template = prompt_path.read_text(encoding="utf-8")

            # 调用LLM生成标题
            title_text = await self._call_llm_for_title(
                prompt_template,
                original_title,
                video_description,
                api_key,
                base_url,
                model,
            )

            # 解析并验证返回的标题
            title = self._parse_llm_title(title_text)

            if title:
                logger.info(f"LLM生成标题成功: {title}")
            else:
                logger.warning("LLM未生成有效标题")

            return title

        except Exception as e:
            logger.error(f"LLM标题生成失败: {str(e)}")
            return None

    async def _call_llm_for_title(
        self,
        prompt_template: str,
        original_title: str,
        description: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> str:
        """调用LLM生成标题"""
        user_input = f"""原始标题：{original_title}
视频简介：
{description}"""
        return await llm_complete(
            prompt_template,
            user_input,
            api_key,
            model=model,
            base_url=base_url,
            temperature=0.7,
            # 给推理类模型（如 DeepSeek-R1 / deepseek-v4-flash）留足预算：
            # max_tokens 限制的是 completion（含 reasoning_content 思考过程）总量，
            # 设得太小会导致思考过程耗尽配额、正式标题为空（finish_reason='length'）。
            max_tokens=2048,
            debug_label="LLM标题生成",
        )

    def _parse_llm_title(self, title_text: str) -> Optional[str]:
        """解析LLM返回的标题文本

        Args:
            title_text: LLM返回的标题文本

        Returns:
            解析后的标题，无效返回None
        """
        try:
            # 按行分割，取第一个非空行
            lines = title_text.split("\n")

            for line in lines:
                line = line.strip()

                # 跳过空行
                if not line:
                    continue

                # 跳过说明性文字
                if (
                    line.startswith("#")
                    or line.startswith("以下是")
                    or line.startswith("标题")
                ):
                    continue

                # 移除可能的引号或markdown符号
                line = line.strip("`'*\"")

                # 检查标题长度（15-30个汉字，不超过80字符）
                if 10 <= len(line) <= 80:
                    return line

                # 如果长度合理但偏短，也接受
                if 5 <= len(line) < 10:
                    logger.warning(f"LLM生成的标题偏短: {line}")
                    return line

            return None

        except Exception as e:
            logger.debug(f"解析LLM标题失败: {str(e)}")
            return None

    def optimize_description(self, youtube_video: YouTubeVideo) -> str:
        """优化描述"""
        try:
            description = youtube_video.description.strip()

            # 添加B站友好的描述格式
            bilibili_description = """
📚 视频介绍：
本视频来源于YouTube，经过翻译和优化，仅供学习交流使用。

🎯 学习要点：
• 实用的技术讲解
• 清晰的步骤演示
• 详细的代码示例

💻 技术栈：
根据视频内容而定

📖 相关资源：
如需获取源码或更多学习资料，请关注原视频频道

🌟 原视频信息：
频道：{channel}
发布时间：{publish_date}
观看次数：{views:,}

⚠️ 免责声明：
本视频为转载内容，版权归原作者所有，仅用于学习和交流目的。
如涉及版权问题，请联系删除。

🔔 关注我们：
如果这个视频对你有帮助，别忘了点赞、收藏和关注哦！
有问题欢迎在评论区讨论~
            """.format(
                channel=youtube_video.channel_title,
                publish_date=youtube_video.published_at.strftime("%Y-%m-%d"),
                views=youtube_video.view_count,
            )

            # 如果原描述有关键信息，也保留一部分
            if description and len(description) > 50:
                bilibili_description += f"\n\n📝 原描述摘要：\n{description[:500]}..."

            return bilibili_description.strip()

        except Exception:
            return youtube_video.description

    async def generate_tags(
        self,
        youtube_video: YouTubeVideo,
        youtuber_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> List[str]:
        """生成标签

        Args:
            youtube_video: YouTube视频对象
            youtuber_name: YouTuber名称（从文件夹名提取）
            description: 视频简介（用于LLM生成标签）

        Returns:
            标签列表（包含YouTuber名称）
        """
        try:
            tags = []

            # 如果提供了YouTuber名称，优先添加
            if youtuber_name:
                tags.append(youtuber_name)

            # 如果有视频简介，使用LLM生成标签
            if description:
                try:
                    llm_tags = await self.generate_tags_with_llm(description)
                    if llm_tags:
                        tags.extend(llm_tags)
                        logger.info(f"使用LLM生成的标签: {', '.join(llm_tags)}")
                except Exception as e:
                    logger.warning(f"LLM标签生成失败，使用备用方案: {str(e)}")

            # 如果LLM未生成标签或生成失败，使用原标签
            if not tags or len(tags) <= (1 if youtuber_name else 0):
                # 从原标签中提取
                for tag in youtube_video.tags[:10]:  # 限制标签数量
                    if len(tag) < 20:  # 过滤过长的标签
                        tags.append(tag)

                # 添加基础标签
                text_to_analyze = (
                    f"{youtube_video.title} {youtube_video.description}".lower()
                )

                for hot_tag in self.hot_tags:
                    if hot_tag.lower() in text_to_analyze and hot_tag not in tags:
                        tags.append(hot_tag)

                # 根据语言添加标签
                if youtube_video.language:
                    if "en" in youtube_video.language:
                        tags.append("英语")
                    elif "zh" in youtube_video.language:
                        tags.append("中文")

            # 去重并限制数量
            tags = list(set(tags))[:12]  # B站标签限制

            return tags

        except Exception:
            return ["学习", "编程", "教程"]

    def determine_category(self, youtube_video: YouTubeVideo) -> int:
        """确定视频分类"""
        try:
            # 根据内容和关键词确定分类
            text = f"{youtube_video.title} {youtube_video.description} {' '.join(youtube_video.tags)}".lower()

            # 知识区 (122)
            knowledge_keywords = ["tutorial", "learn", "education", "course", "study"]
            if any(keyword in text for keyword in knowledge_keywords):
                return 122

            # 科学科普 (201)
            science_keywords = [
                "science",
                "research",
                "physics",
                "chemistry",
                "biology",
                "math",
            ]
            if any(keyword in text for keyword in science_keywords):
                return 201

            # 社科人文 (124)
            social_keywords = [
                "history",
                "philosophy",
                "psychology",
                "sociology",
                "culture",
            ]
            if any(keyword in text for keyword in social_keywords):
                return 124

            # 数码 (95)
            tech_keywords = ["phone", "computer", "hardware", "review", "gadget"]
            if any(keyword in text for keyword in tech_keywords):
                return 95

            # 默认知识区
            return 122

        except Exception:
            return 122  # 默认知识区

    def generate_repost_description(self, youtube_video: YouTubeVideo) -> str:
        """生成转载说明"""
        return f"""本视频转载自YouTube频道「{youtube_video.channel_title}」

仅供学习交流使用，版权归原作者所有。
如需了解更多内容，请访问原频道观看完整视频。""".strip()

    def generate_dynamic_content(self, youtube_video: YouTubeVideo) -> str:
        """生成动态内容"""
        try:
            return ""
        except Exception:
            return "分享了一个有趣的技术视频，一起学习进步！"

    async def generate_tags_with_llm(self, video_description: str) -> List[str]:
        """使用LLM根据视频简介生成标签

        Args:
            video_description: 视频简介内容

        Returns:
            生成的标签列表
        """
        try:
            # 检查API密钥
            api_key = settings.openai_api_key
            if not api_key:
                logger.warning("未设置OPENAI_API_KEY，跳过LLM标签生成")
                return []

            # 获取base_url（可选）
            base_url = settings.openai_base_url

            # 获取模型配置
            model = settings.openai_model

            # 读取prompt模板
            project_root = Path(__file__).parent.parent.parent
            prompt_path = project_root / "prompts" / "generate_tags.md"
            if not prompt_path.exists():
                logger.error(f"Prompt文件不存在: {prompt_path}")
                return []

            prompt_template = prompt_path.read_text(encoding="utf-8")

            # 调用LLM生成标签
            tags_text = await self._call_llm_for_tags(
                prompt_template, video_description, api_key, base_url, model
            )

            # 解析返回的标签
            tags = self._parse_llm_tags(tags_text)

            if tags:
                logger.info(f"LLM生成标签成功: {', '.join(tags)}")
            else:
                logger.warning("LLM未生成有效标签")

            return tags

        except Exception as e:
            logger.error(f"LLM标签生成失败: {str(e)}")
            return []

    async def _call_llm_for_tags(
        self,
        prompt_template: str,
        description: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> str:
        """调用LLM生成标签"""
        return await llm_complete(
            prompt_template,
            description,
            api_key,
            model=model,
            base_url=base_url,
            temperature=0.5,
            # 推理类模型的思考过程同样计入 max_tokens 配额，需留足余量，
            # 否则可能因思考耗尽配额而返回空内容。
            max_tokens=2048,
            debug_label="LLM标签生成",
        )

    def _parse_llm_tags(self, tags_text: str) -> List[str]:
        """解析LLM返回的标签文本

        Args:
            tags_text: LLM返回的标签文本

        Returns:
            解析后的标签列表
        """
        try:
            tags = []

            # 按行分割
            lines = tags_text.split("\n")

            for line in lines:
                line = line.strip()

                # 跳过空行
                if not line:
                    continue

                # 跳过说明性文字
                if (
                    line.startswith("#")
                    or line.startswith("以下是")
                    or line.startswith("标签")
                ):
                    continue

                # 移除可能的序号前缀（如 "1. " 或 "1: "）
                if line[0].isdigit() and (": " in line[:3] or ". " in line[:3]):
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        line = parts[1]

                # 移除markdown列表符号
                line = line.lstrip("-*•")

                line = line.strip()

                # 检查标签长度（不超过5个汉字）
                if len(line) <= 5:
                    tags.append(line)

            # 去重并限制数量
            return list(dict.fromkeys(tags))[:6]

        except Exception as e:
            logger.debug(f"解析LLM标签失败: {str(e)}")
            return []
