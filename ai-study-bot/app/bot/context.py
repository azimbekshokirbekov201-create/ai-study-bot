from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.database import Database


@dataclass
class Runtime:
    settings: Settings
    database: Database
    ai: Any = None
    bot: Any = None
    redis: Any = None
    polling_task: Any = None
    worker_task: Any = None
    ready: bool = False
