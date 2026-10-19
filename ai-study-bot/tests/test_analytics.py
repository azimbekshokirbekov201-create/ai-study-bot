from datetime import timedelta

from app.database.base import utcnow
from app.models import RewardEvent, User, UserProgress
from app.services.analytics import leaderboard, recommendation


async def test_leaderboard_periods_rank_ties_fairly(session):
    users = [User(telegram_id=i, display_name=f"Student {i}") for i in (31, 32, 33)]
    session.add_all(users)
    await session.flush()
    now = utcnow()
    session.add_all(
        [
            RewardEvent(user_id=users[0].id, source_key="today1", points=20, awarded_at=now),
            RewardEvent(user_id=users[1].id, source_key="today2", points=20, awarded_at=now),
            RewardEvent(
                user_id=users[2].id,
                source_key="old",
                points=100,
                awarded_at=now - timedelta(days=40),
            ),
        ]
    )
    await session.flush()
    daily, mine = await leaderboard(session, "day", users[1].id, now)
    assert [row["rank"] for row in daily] == [1, 1]
    assert mine["points"] == 20
    all_time, _ = await leaderboard(session, "all", now=now)
    assert all_time[0]["user_id"] == users[2].id
    assert [row["rank"] for row in all_time] == [1, 2, 2]


def test_recommendations_require_evidence_and_respect_level_bounds():
    assert recommendation(None, "B1") == ("B1", 1)
    assert recommendation(UserProgress(answered=5, correct=1), "A1") == ("A1", 1)
    assert recommendation(UserProgress(answered=5, correct=5), "B2") == ("C1", 3)
    assert recommendation(UserProgress(answered=5, correct=5), "C1") == ("C1", 3)
