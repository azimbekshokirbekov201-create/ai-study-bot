from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.database.base import utcnow
from app.models import (
    AttemptQuestion,
    Question,
    QuestionOption,
    QuizAnswer,
    RewardEvent,
    Subject,
    User,
    UserProgress,
)
from app.services.errors import UserError
from app.services.quizzes import QuizService


async def content(session):
    user = User(telegram_id=22, display_name="Student")
    subject = Subject(code="sat_math", title_uz="Matematika", title_en="Math")
    session.add_all([user, subject])
    await session.flush()
    q = Question(
        code="original-1",
        subject_id=subject.id,
        topic="algebra",
        prompt_uz="2+3?",
        prompt_en="2+3?",
        correct_option=1,
        explanation_uz="2+3=5",
        explanation_en="2+3=5",
        difficulty=2,
    )
    session.add(q)
    await session.flush()
    session.add_all(
        [
            QuestionOption(question_id=q.id, position=i, text_uz=str(i + 4), text_en=str(i + 4))
            for i in range(4)
        ]
    )
    await session.flush()
    return user, subject, q


async def test_scoring_snapshots_duplicate_answers_and_rewards(session, settings):
    user, subject, question = await content(session)
    svc = QuizService(session, settings)
    attempt = await svc.start(user.id, "en", subject_code=subject.code)
    question.correct_option = 3  # Historical snapshot must still use option 1.
    result = await svc.answer(user.id, attempt.id, 0, 1)
    assert result.correct and result.points == 15
    assert result.attempt.status == "completed"
    repeat = await svc.answer(user.id, attempt.id, 0, 0)
    assert repeat.duplicate
    assert await session.scalar(select(func.count()).select_from(QuizAnswer)) == 1
    question.correct_option = 1
    attempt2 = await svc.start(user.id, "en", subject_code=subject.code)
    assert (await svc.answer(user.id, attempt2.id, 0, 1)).points == 0
    assert await session.scalar(select(func.sum(RewardEvent.points))) == 15
    progress = await session.scalar(select(UserProgress))
    assert (progress.answered, progress.correct) == (2, 2)


async def test_expired_and_foreign_attempts_are_rejected(session, settings):
    user, subject, _ = await content(session)
    svc = QuizService(session, settings)
    now = utcnow()
    attempt = await svc.start(user.id, "uz", subject_code=subject.code, now=now)
    with pytest.raises(UserError):
        await svc.answer(999, attempt.id, 0, 1)
    result = await svc.answer(user.id, attempt.id, 0, 1, now=now + timedelta(hours=1))
    assert result.expired
    assert await session.scalar(select(func.count()).select_from(QuizAnswer)) == 0


async def test_daily_challenge_cannot_restart_and_has_four_snapshot_options(session, settings):
    user, _, _ = await content(session)
    svc = QuizService(session, settings)
    first = await svc.start(user.id, "uz", kind="daily")
    await svc.answer(user.id, first.id, 0, 1)
    second = await svc.start(user.id, "uz", kind="daily")
    assert first.id == second.id
    assert len((await session.get(AttemptQuestion, (first.id, 0))).options) == 4
