from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import aware, utcnow
from app.models import Subscription


async def premium_until(session: AsyncSession, user_id: int, now: datetime | None = None):
    now = now or utcnow()
    rows = (
        await session.scalars(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.revoked_at.is_(None),
                Subscription.ends_at > now,
            )
            .order_by(Subscription.starts_at)
        )
    ).all()
    cursor = now
    for row in rows:
        if aware(row.starts_at) > cursor:
            break
        cursor = max(cursor, aware(row.ends_at))
    return cursor if cursor > now else None


async def is_premium(session: AsyncSession, user_id: int, now: datetime | None = None) -> bool:
    return await premium_until(session, user_id, now) is not None


async def grant_subscription(
    session: AsyncSession, user_id: int, days: int, *, payment_id=None, source="admin"
):
    # Non-overlapping renewal intervals preserve independent refund/revocation.
    now = utcnow()
    current_end = await premium_until(session, user_id, now)
    end = max(now, aware(current_end)) if current_end else now
    subscription = Subscription(
        user_id=user_id,
        payment_id=payment_id,
        source=source,
        starts_at=end,
        ends_at=end + timedelta(days=days),
    )
    session.add(subscription)
    await session.flush()
    return subscription
