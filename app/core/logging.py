import logging
from typing import Final

import structlog

_DEFAULT_LEVEL: Final[str] = "INFO"


def _resolve_level(level: str) -> int:
    normalized = level.strip().upper() or _DEFAULT_LEVEL
    return logging._nameToLevel.get(normalized, logging.INFO)


def configure_logging(level: str) -> None:
    log_level = _resolve_level(level)
    logging.basicConfig(level=log_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )
