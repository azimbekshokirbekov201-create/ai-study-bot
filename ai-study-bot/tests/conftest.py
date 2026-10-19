import os

import pytest
import pytest_asyncio

from app import models  # noqa: F401
from app.config import Settings
from app.database import Base, Database


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"),
    )


@pytest_asyncio.fixture
async def database(settings):
    db = Database(settings)
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield db
    await db.close()


@pytest_asyncio.fixture
async def session(database):
    async with database.sessions() as session:
        async with session.begin():
            yield session
