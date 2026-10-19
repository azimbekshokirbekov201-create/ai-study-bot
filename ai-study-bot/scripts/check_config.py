"""Validate configuration/connectivity without printing credential values."""

import asyncio
import json

from sqlalchemy import func, select

from app.config import get_settings
from app.database import Database
from app.models import Lesson, Question, User


async def main():
    settings = get_settings()
    db = Database(settings)
    try:
        await db.healthy()
        async with db.sessions() as session:
            counts = {
                model.__tablename__: await session.scalar(select(func.count()).select_from(model))
                for model in (User, Lesson, Question)
            }
        print(
            json.dumps(
                {
                    "database": "reachable",
                    "bot_configured": bool(settings.bot_token),
                    "ai_configured": bool(settings.openai_api_key),
                    "mode": settings.bot_mode,
                    "admin_count": len(settings.admin_ids),
                    "admin_api_enabled": bool(settings.admin_api_token),
                    "tts_enabled": settings.tts_enabled,
                    "transcription_enabled": settings.transcription_enabled,
                    "counts": counts,
                },
                indent=2,
            )
        )
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
