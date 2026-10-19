from aiogram.types import User as TelegramUser
from sqlalchemy import func, select

from app.models import User
from app.repositories.users import register_user


async def test_registration_is_idempotent_and_uzbek_by_default(session):
    telegram = TelegramUser(id=101, first_name="Aziza", is_bot=False)
    user = await register_user(session, telegram)
    assert user.language == "uz"
    assert user.registered_at is not None
    telegram = telegram.model_copy(update={"first_name": "Aziza A"})
    again = await register_user(session, telegram)
    assert again.id == user.id
    assert again.display_name == "Aziza A"
    assert await session.scalar(select(func.count()).select_from(User)) == 1


def test_configuration_rejects_unsafe_production():
    import pytest
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, app_env="development", database_url="sqlite+aiosqlite:///unsafe.db"
        )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, bot_mode="webhook", public_base_url="http://example.com")
