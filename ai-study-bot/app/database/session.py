from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


class Database:
    def __init__(self, settings: Settings):
        url = settings.database_url.get_secret_value()
        kwargs = {"pool_pre_ping": True}
        if url.startswith("postgresql"):
            kwargs |= {
                "pool_size": 10,
                "max_overflow": 10,
                "pool_timeout": 15,
                "connect_args": {"server_settings": {"statement_timeout": "90000"}},
            }
        self.engine = create_async_engine(url, **kwargs)
        if url.startswith("sqlite"):

            @event.listens_for(self.engine.sync_engine, "connect")
            def enable_fks(connection, _record):
                connection.execute("PRAGMA foreign_keys=ON")

        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def healthy(self) -> bool:
        async with self.sessions() as session:
            await session.execute(text("SELECT 1"))
        return True

    async def close(self):
        await self.engine.dispose()


async def advisory_lock(session: AsyncSession, namespace: int, key: int) -> None:
    if session.bind.dialect.name == "postgresql":
        # Bigint IDs are hashed by PostgreSQL to a stable signed 64-bit lock key.
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"{namespace}:{key}"},
        )
