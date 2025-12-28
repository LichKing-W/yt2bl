"""B站内容优化模块"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..utils.logger import logger
from ..youtube.models import YouTubeVideo
from .models import BilibiliVideo, BilibiliCategory


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

        # 标题关键词映射（英文到中文）
        self.title_keywords = {
            "tutorial": "教程",
            "guide": "指南",
            "introduction": "入门",
            "advanced": "进阶",
            "master": "精通",
            "course": "课程",
            "lecture": "讲座",
            "workshop": "工作坊",
            "project": "项目",
            "practice": "实战",
            "tips": "技巧",
            "tricks": "诀窍",
            "how to": "如何",
            "learn": "学习",
            "build": "构建",
            "create": "创建",
            "develop": "开发",
            "design": "设计",
            "implement": "实现",
            "optimize": "优化",
            "debug": "调试",
            "test": "测试",
            "deploy": "部署",
            "programming": "编程",
            "coding": "代码",
            "software": "软件",
            "development": "开发",
            "engineering": "工程",
            "computer": "计算机",
            "science": "科学",
            "technology": "技术",
            "innovation": "创新",
        }

    def optimize_for_bilibili(
        self, youtube_video: YouTubeVideo, video_path: str
    ) -> BilibiliVideo:
        """将YouTube视频优化为B站格式"""
        try:
            logger.info(f"开始优化视频内容: {youtube_video.title}")

            # 获取视频文件夹路径
            video_path_obj = Path(video_path)
            video_folder = video_path_obj.parent

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

            # 优化标题
            optimized_title = self.optimize_title(youtube_video.title)

            # 生成标签
            optimized_tags = self.generate_tags(youtube_video)

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
                source=f"来源：YouTube - {youtube_video.channel_title}",
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
                copyright=2,
                source=f"来源：YouTube - {youtube_video.channel_title}",
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

    def optimize_title(self, original_title: str) -> str:
        """优化标题"""
        try:
            # 清理标题
            title = original_title.strip()

            # 移除一些不适合B站的符号
            title = re.sub(r"[|]{2,}", "｜", title)
            title = re.sub(r"\s+", " ", title)

            # 翻译关键词
            for en_keyword, zh_keyword in self.title_keywords.items():
                title = re.sub(
                    r"\b" + re.escape(en_keyword) + r"\b",
                    zh_keyword,
                    title,
                    flags=re.IGNORECASE,
                )

            # 检查标题长度
            if len(title) > 80:  # B站标题限制
                # 尝试缩短标题
                title = title[:77] + "..."

            # 添加一些B站友好的元素
            if not any(symbol in title for symbol in ["【", "「", "『"]):
                title = f"{title}"

            return title

        except Exception:
            return original_title

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

    def generate_tags(self, youtube_video: YouTubeVideo) -> List[str]:
        """生成标签"""
        try:
            tags = []

            # 基础标签
            tags.extend(["学习", "编程", "教程", "技术"])

            # 从原标签中提取
            for tag in youtube_video.tags[:10]:  # 限制标签数量
                if len(tag) < 20:  # 过滤过长的标签
                    tags.append(tag)

            # 根据标题和描述生成标签
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
        return f"""
本视频转载自YouTube频道「{youtube_video.channel_title}」，原视频链接：{youtube_video.url}

已获得原作者许可的转载声明（如果适用）或仅用于学习交流目的。

如需了解更多内容，请访问原频道观看完整视频。
        """.strip()

    def generate_dynamic_content(self, youtube_video: YouTubeVideo) -> str:
        """生成动态内容"""
        try:
            return ""
        except Exception:
            return "分享了一个有趣的技术视频，一起学习进步！"
