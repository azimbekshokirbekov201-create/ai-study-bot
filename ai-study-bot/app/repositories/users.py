from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.database.session import advisory_lock
from app.models import User


async def register_user(session: AsyncSession, telegram: TelegramUser) -> User:
    await advisory_lock(session, 2, telegram.id)
    # The advisory lock serializes user updates without taking a FOR UPDATE row
    # lock that would block foreign keys in separately committed AI reservations.
    user = await session.scalar(select(User).where(User.telegram_id == telegram.id))
    name = telegram.full_name[:128]
    if user is None:
        user = User(telegram_id=telegram.id, display_name=name, username=telegram.username)
        session.add(user)
    else:
        user.display_name = name
        user.username = telegram.username
        user.last_seen_at = utcnow()
        user.blocked = False
    await session.flush()
    return user
