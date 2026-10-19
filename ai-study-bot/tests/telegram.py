import asyncio
from datetime import UTC, datetime

from aiogram.client.session.base import BaseSession
from aiogram.types import Message, User


class RecordingSession(BaseSession):
    """Offline Telegram transport used exclusively in tests."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):  # noqa: ASYNC109 - aiogram interface
        self.calls.append(method)
        if method.__api_method__ == "getUpdates":
            await asyncio.sleep(0.05)
            return []
        if method.__api_method__ == "getMe":
            return User(id=bot.id, is_bot=True, first_name="Study", username="test_study_bot")
        if method.__api_method__ in ("sendMessage", "sendInvoice", "sendAudio"):
            return Message.model_validate(
                {
                    "message_id": len(self.calls),
                    "date": datetime.now(UTC),
                    "chat": {"id": method.chat_id, "type": "private"},
                    "text": getattr(method, "text", ""),
                },
                context={"bot": bot},
            )
        return True

    async def stream_content(
        self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True
    ):  # noqa: ASYNC109 - aiogram interface
        yield b""


def message_update(update_id, text, user_id=101, **extra):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": 1700000000,
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Aziza"},
            "text": text,
            **extra,
        },
    }


def callback_update(update_id, data, user_id=101):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": str(update_id),
            "chat_instance": "test",
            "from": {"id": user_id, "is_bot": False, "first_name": "Aziza"},
            "data": data,
            "message": {
                "message_id": 1,
                "date": 1700000000,
                "chat": {"id": user_id, "type": "private"},
            },
        },
    }
