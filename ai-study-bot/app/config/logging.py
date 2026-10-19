import json
import logging
from datetime import UTC, datetime


class SafeFormatter(logging.Formatter):
    """Deliberately omit exception messages, request URLs and user text."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "event": record.msg if isinstance(record.msg, str) else "application_event",
                "error_type": record.exc_info[0].__name__ if record.exc_info else None,
            }
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    for name in ("httpx", "httpcore", "openai", "aiogram", "sqlalchemy.engine", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
