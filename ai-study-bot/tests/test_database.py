import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.models import Question, Subject, User, UserProgress


async def test_unique_identity_and_foreign_keys_are_database_constraints(session):
    session.add(User(telegram_id=1001, display_name="One"))
    await session.flush()
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(User(telegram_id=1001, display_name="Duplicate"))
            await session.flush()
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(UserProgress(user_id=999999, subject_id=999999, topic="invalid"))
            await session.flush()
    assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_invalid_answers_are_rejected_and_progress_cascades(session):
    user = User(telegram_id=1002, display_name="Two")
    subject = Subject(code="subject", title_uz="Fan", title_en="Subject")
    session.add_all([user, subject])
    await session.flush()
    session.add(UserProgress(user_id=user.id, subject_id=subject.id, topic="algebra"))
    await session.flush()
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(
                Question(
                    code="bad",
                    subject_id=subject.id,
                    topic="algebra",
                    difficulty=4,
                    correct_option=4,
                    prompt_uz="?",
                    prompt_en="?",
                    explanation_uz="!",
                    explanation_en="!",
                )
            )
            await session.flush()
    await session.execute(delete(User).where(User.id == user.id))
    assert await session.scalar(select(func.count()).select_from(UserProgress)) == 0
