from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage
from sqlalchemy import select

from app.admin.service import queue_broadcast
from app.bot.context import Runtime
from app.models import BroadcastDelivery, User
from app.services.worker import deliver_one, maintenance
from tests.telegram import RecordingSession


async def test_worker_delivers_persisted_job_and_respects_late_optout(database, settings):
    bot = Bot("123456:TEST_ONLY_TOKEN", session=RecordingSession())
    runtime = Runtime(settings, database, bot=bot)
    async with database.sessions() as session, session.begin():
        users = [User(telegram_id=i, display_name=str(i)) for i in (801, 802)]
        session.add_all(users)
        await session.flush()
        job = await queue_broadcast(session, "Read a page today", "telegram:9001")
        users[1].announcements_enabled = False
    assert (await deliver_one(runtime))[0]
    assert (await deliver_one(runtime))[0]
    assert not (await deliver_one(runtime))[0]
    await maintenance(runtime)
    async with database.sessions() as session:
        rows = (
            await session.scalars(
                select(BroadcastDelivery)
                .where(BroadcastDelivery.broadcast_id == job.id)
                .order_by(BroadcastDelivery.user_id)
            )
        ).all()
        assert [r.status for r in rows] == ["sent", "skipped"]
    assert len(bot.session.calls) == 1


async def test_worker_flood_wait_and_blocked_recipient(database, settings):
    class FailingBot:
        error = TelegramRetryAfter(SendMessage(chat_id=1, text="test"), "test", retry_after=2)

        async def send_message(self, *args, **kwargs):
            raise self.error

    bot = FailingBot()
    runtime = Runtime(settings, database, bot=bot)
    async with database.sessions() as session, session.begin():
        user = User(telegram_id=803, display_name="Recipient")
        session.add(user)
        await session.flush()
        await queue_broadcast(session, "Study", "telegram:9001")
    _, delay = await deliver_one(runtime)
    assert delay == 3
    async with database.sessions() as session:
        delivery = await session.scalar(select(BroadcastDelivery))
        assert delivery.attempts == 0 and delivery.status == "queued"
    bot.error = TelegramForbiddenError(SendMessage(chat_id=1, text="test"), "test")
    await deliver_one(runtime)
    async with database.sessions() as session:
        assert (await session.scalar(select(BroadcastDelivery))).status == "blocked"
        assert (await session.scalar(select(User))).blocked
