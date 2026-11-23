import logging
from pathlib import Path
from typing import ClassVar

from config.config import BACKEND_DIR, get_settings
from config.context import request_id

SUCCESS = logging.INFO + 5
logging.addLevelName(SUCCESS, "SUCCESS")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = str(request_id.get() or "SYSTEM")
        return True


class OnlineExceptionFormatter(logging.Formatter):
    default_time_format: ClassVar[str] = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return (
            formatted.replace("\r\n", " | ")
            .replace("\n", " | ")
            .replace("\r", " | ")
        )


def _level_from_name(level_name: str) -> int:
    level = logging.getLevelNamesMapping().get(level_name.upper())
    if level is None:
        raise ValueError(f"Invalid LOG_LEVEL: {level_name}")
    return level


def configure_logging() -> None:
    settings = get_settings()
    level = _level_from_name(settings.log_level)
    formatter = OnlineExceptionFormatter(
        "%(asctime)-15s - %(request_id)s - %(name)-5s - %(levelname)s - "
        "[%(filename)s:%(lineno)s - %(funcName)s()] - %(message)s"
    )
    context_filter = ContextFilter()
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    handlers = {
        getattr(handler, "_edusuggest_handler", None): handler
        for handler in root_logger.handlers
        if getattr(handler, "_edusuggest_handler", None)
    }

    console_handler = handlers.get("console")
    if console_handler is None:
        console_handler = logging.StreamHandler()
        console_handler._edusuggest_handler = "console"
        root_logger.addHandler(console_handler)

    log_path = Path(settings.system_log_file)
    if not log_path.is_absolute():
        log_path = BACKEND_DIR / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = handlers.get("file")
    if file_handler is None:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler._edusuggest_handler = "file"
        root_logger.addHandler(file_handler)

    for handler in (console_handler, file_handler):
        handler.setLevel(level)
        handler.setFormatter(formatter)
        handler.addFilter(context_filter)

    logging.getLogger("sqlalchemy.engine.Engine").setLevel(max(level, logging.INFO))


configure_logging()
logger = logging.getLogger("app.fastapi")


def log_success(message: str, *args: object) -> None:
    logger.log(SUCCESS, message, *args)
