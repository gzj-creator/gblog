import logging
import json
import sys
import os
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON 格式日志（生产环境）"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    """彩色控制台日志（开发环境）"""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.utcfromtimestamp(record.created).strftime("%H:%M:%S")
        msg = record.getMessage()
        formatted = f"{color}{timestamp} [{record.levelname:<7}]{self.RESET} {record.name}: {msg}"
        if record.exc_info and record.exc_info[0]:
            formatted += "\n" + self.formatException(record.exc_info)
        return formatted


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志"""
    env = os.getenv("ENVIRONMENT", "development")
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ColorFormatter())

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    # 降低第三方库日志级别
    for name in ("httpcore", "httpx", "chromadb", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取模块 logger"""
    return logging.getLogger(name)
