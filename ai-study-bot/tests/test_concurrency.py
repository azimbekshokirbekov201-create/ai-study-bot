import asyncio

import pytest
from aiogram.types import Update
from sqlalchemy import func, select

from app.ai.quota import UsageBudget
from app.models import AIUsage, QuizAnswer, RewardEvent, User
from app.services.errors import QuotaExceeded
from app.services.quizzes import QuizService
from tests.telegram import callback_update, message_update
from tests.test_ai import FakeProvider
from tests.test_handlers import setup
from tests.test_quizzes import content


def require_postgres(database):
    if database.engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL concurrency semantics require TEST_DATABASE_URL")


async def test_concurrent_quota_reservations_cannot_exceed_daily_limit(database, settings):
    require_postgres(database)
    async with database.sessions() as session, session.begin():
        user = User(telegram_id=7001, display_name="Concurrent")
        session.add(user)
        await session.flush()
    cfg = settings.model_copy(update={"ai_free_daily_requests": 2})
    budget = UsageBudget(database, cfg)
    results = await asyncio.gather(
        *(budget.reserve(user.id, "tutor", 100) for _ in range(8)), return_exceptions=True
    )
    assert sum(not isinstance(r, Exception) for r in results) == 2
    assert sum(isinstance(r, QuotaExceeded) for r in results) == 6


async def test_concurrent_quiz_answers_award_once(database, settings):
    require_postgres(database)
    async with database.sessions() as session, session.begin():
        user, subject, _ = await content(session)
        attempt = await QuizService(session, settings).start(
            user.id, "en", subject_code=subject.code
        )

    async def submit():
        async with database.sessions() as session, session.begin():
            return await QuizService(session, settings).answer(user.id, attempt.id, 0, 1)

    results = await asyncio.gather(*(submit() for _ in range(5)))
    assert sum(not result.duplicate for result in results) == 1
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(QuizAnswer)) == 1
        assert await session.scalar(select(func.count()).select_from(RewardEvent)) == 1


async def test_ai_reservation_does_not_deadlock_registration_update_lock(database, settings):
    require_postgres(database)
    dispatcher, bot, _, runtime = await setup(database, settings)
    runtime.ai.provider = FakeProvider()
    for data in [
        message_update(1, "/start"),
        callback_update(2, "nav:ai:ask"),
        message_update(3, "Explain 2/3 + 1/3"),
    ]:
        async with asyncio.timeout(10):
            await dispatcher.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    async with database.sessions() as session:
        assert (await session.scalar(select(AIUsage))).requests == 1
    await runtime.ai.close()
