"""配置管理模块"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """应用配置"""

    def __init__(self):
        # YouTube配置
        self.youtube_api_key: Optional[str] = None

        # Bilibili配置
        self.bilibili_sessdata: Optional[str] = None
        self.bilibili_bili_jct: Optional[str] = None
        self.bilibili_dedeuser_id: Optional[str] = None

        # 下载配置
        self.download_path: str = "./data"
        self.max_video_size_mb: int = 500
        self.video_quality: str = "720p"
        self.youtube_cookies_file: Optional[str] = None  # YouTube cookies文件路径

        # 上传配置
        self.upload_cooldown_hours: int = 2
        self.auto_publish: bool = False

        # OpenAI/LLM配置
        self.openai_api_key: Optional[str] = None
        self.openai_base_url: Optional[str] = None
        self.openai_model: str = "gpt-4o-mini"  # 默认模型

        # 日志配置
        self.log_level: str = "INFO"
        self.log_file: str = "./logs/app.log"

        # FFmpeg配置
        self.ffmpeg_hwaccel: str = "auto"  # auto, nvenc, qsv, amf, videotoolbox, vaapi, none
        self.ffmpeg_preset: str = "fast"  # 编码器预设 (fast, medium, slow, etc.)

        self._load_env()
        self._ensure_directories()

    def _load_env(self) -> None:
        """加载环境变量"""
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip().lower()
                        value = value.strip()

                        # 映射环境变量到属性
                        attr_mapping = {
                            "youtube_api_key": "youtube_api_key",
                            "youtube_cookies_file": "youtube_cookies_file",
                            "bilibili_sessdata": "bilibili_sessdata",
                            "bilibili_bili_jct": "bilibili_bili_jct",
                            "bilibili_dedeuserid": "bilibili_dedeuser_id",
                            "download_path": "download_path",
                            "max_video_size_mb": "max_video_size_mb",
                            "video_quality": "video_quality",
                            "upload_cooldown_hours": "upload_cooldown_hours",
                            "auto_publish": "auto_publish",
                            "openai_api_key": "openai_api_key",
                            "openai_base_url": "openai_base_url",
                            "openai_model": "openai_model",
                            "log_level": "log_level",
                            "log_file": "log_file",
                            "ffmpeg_hwaccel": "ffmpeg_hwaccel",
                            "ffmpeg_preset": "ffmpeg_preset",
                        }

                        attr_name = attr_mapping.get(key)
                        if attr_name:
                            if key.endswith("_mb") or key.endswith("_hours"):
                                try:
                                    setattr(self, attr_name, int(value))
                                except ValueError:
                                    pass
                            elif key == "auto_publish":
                                setattr(self, attr_name, value.lower() in ("true", "1", "yes"))
                            else:
                                setattr(self, attr_name, value)

    def _ensure_directories(self) -> None:
        """确保目录存在"""
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
