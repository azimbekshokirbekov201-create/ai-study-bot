from datetime import datetime, timedelta

from sqlalchemy import case, func, select

from app.database.base import utcnow
from app.models import (
    Achievement,
    QuizAnswer,
    QuizAttempt,
    RewardEvent,
    User,
    UserAchievement,
    UserProgress,
)


def period_start(period: str, now: datetime | None = None):
    now = now or utcnow()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        return midnight
    if period == "week":
        return midnight - timedelta(days=midnight.weekday())
    if period == "month":
        return midnight.replace(day=1)
    if period == "all":
        return None
    raise ValueError("Invalid leaderboard period")


async def leaderboard(session, period="week", user_id=None, now=None):
    query = select(
        RewardEvent.user_id.label("user_id"), func.sum(RewardEvent.points).label("points")
    )
    start = period_start(period, now)
    if start:
        query = query.where(RewardEvent.awarded_at >= start)
    totals = query.group_by(RewardEvent.user_id).subquery()
    ranked = select(
        totals.c.user_id,
        totals.c.points,
        func.rank().over(order_by=totals.c.points.desc()).label("rank"),
    ).subquery()
    rows = (
        (
            await session.execute(
                select(ranked, User.display_name)
                .join(User, User.id == ranked.c.user_id)
                .order_by(ranked.c.rank, ranked.c.user_id)
                .limit(20)
            )
        )
        .mappings()
        .all()
    )
    mine = None
    if user_id:
        mine = (
            (await session.execute(select(ranked).where(ranked.c.user_id == user_id)))
            .mappings()
            .first()
        )
    return rows, mine


async def statistics(session, user_id: int):
    completed = await session.scalar(
        select(func.count())
        .select_from(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.status == "completed")
    )
    answered, correct = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(case((QuizAnswer.correct.is_(True), 1), else_=0)), 0),
            )
            .select_from(QuizAnswer)
            .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
            .where(QuizAttempt.user_id == user_id)
        )
    ).one()
    points = await session.scalar(
        select(func.coalesce(func.sum(RewardEvent.points), 0)).where(RewardEvent.user_id == user_id)
    )
    progress = (
        await session.scalars(
            select(UserProgress)
            .where(UserProgress.user_id == user_id)
            .order_by(
                (UserProgress.correct * 1.0 / func.nullif(UserProgress.answered, 0))
                .asc()
                .nulls_last()
            )
        )
    ).all()
    badges = (
        await session.scalars(
            select(Achievement).join(UserAchievement).where(UserAchievement.user_id == user_id)
        )
    ).all()
    return {
        "completed": completed,
        "answered": answered,
        "correct": correct,
        "incorrect": answered - correct,
        "accuracy": correct / answered * 100 if answered else 0.0,
        "points": points,
        "progress": progress,
        "badges": badges,
    }


def recommendation(progress: UserProgress | None, level="B1"):
    levels = ["A1", "A2", "B1", "B2", "C1"]
    if progress is None or progress.answered < 3:
        return level, 1
    accuracy = progress.correct / progress.answered
    if accuracy < 0.6:
        return levels[max(0, levels.index(level) - 1)], 1
    if accuracy >= 0.85 and progress.answered >= 5:
        return levels[min(4, levels.index(level) + 1)], 3
    return level, 2
