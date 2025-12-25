"""日志配置模块"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .config import settings


class Logger:
    """日志管理器"""

    def __init__(self) -> None:
        if RICH_AVAILABLE:
            self.console = Console()
        self._setup_logger()

    def _setup_logger(self) -> None:
        """设置日志配置"""
        # 创建日志目录
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 配置处理器
        handlers = []

        # 文件处理器
        file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handlers.append(file_handler)

        # 控制台处理器
        if RICH_AVAILABLE:
            console_handler = RichHandler(
                console=self.console,
                show_time=True,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter("%(levelname)s: %(message)s")
            )
        handlers.append(console_handler)

        # 配置日志
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(message)s",
            datefmt="[%X]",
            handlers=handlers,
        )

        self.logger = logging.getLogger("youtube_to_bilibili")

    def info(self, message: str) -> None:
        """记录信息日志"""
        self.logger.info(message)

    def error(self, message: str) -> None:
        """记录错误日志"""
        self.logger.error(message)

    def warning(self, message: str) -> None:
        """记录警告日志"""
        self.logger.warning(message)

    def debug(self, message: str) -> None:
        """记录调试日志"""
        self.logger.debug(message)


# 全局日志实例
logger = Logger()
