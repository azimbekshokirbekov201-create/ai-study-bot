import asyncio
import logging
from datetime import timedelta

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import delete, func, select

from app.database.base import utcnow
from app.models import (
    AIConversation,
    AIRequest,
    ApplicationError,
    Broadcast,
    BroadcastDelivery,
    UpdateReceipt,
    User,
)

logger = logging.getLogger(__name__)


async def deliver_one(runtime):
    delay = 0.1
    async with runtime.database.sessions() as session, session.begin():
        delivery = await session.scalar(
            select(BroadcastDelivery)
            .where(BroadcastDelivery.status == "queued")
            .order_by(BroadcastDelivery.broadcast_id, BroadcastDelivery.user_id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if delivery is None:
            return False, 1
        broadcast = await session.get(Broadcast, delivery.broadcast_id)
        user = await session.get(User, delivery.user_id)
        if user.blocked or not user.announcements_enabled:
            delivery.status = "skipped"
            return True, delay
        delivery.attempts += 1
        try:
            await runtime.bot.send_message(user.telegram_id, broadcast.text, parse_mode=None)
            delivery.status = "sent"
        except TelegramForbiddenError:
            user.blocked, delivery.status = True, "blocked"
        except TelegramRetryAfter as exc:
            delivery.attempts -= 1
            delay = min(60, exc.retry_after + 1)
        except Exception as exc:
            delivery.status = "failed" if delivery.attempts >= 3 else "queued"
            session.add(ApplicationError(error_type=type(exc).__name__[:100], location="broadcast"))
            delay = 2
    return True, delay


async def maintenance(runtime):
    now = utcnow()
    async with runtime.database.sessions() as session, session.begin():
        await session.execute(
            delete(AIConversation).where(
                AIConversation.created_at
                < now - timedelta(days=runtime.settings.ai_history_retention_days)
            )
        )
        await session.execute(
            delete(UpdateReceipt).where(UpdateReceipt.processed_at < now - timedelta(days=30))
        )
        # Keep operational errors bounded; financial/audit data is never pruned here.
        await session.execute(
            delete(ApplicationError).where(ApplicationError.created_at < now - timedelta(days=90))
        )
        await session.execute(
            delete(AIRequest).where(AIRequest.created_at < now - timedelta(days=90))
        )
        jobs = (await session.scalars(select(Broadcast).where(Broadcast.status == "queued"))).all()
        for job in jobs:
            remaining = await session.scalar(
                select(func.count())
                .select_from(BroadcastDelivery)
                .where(
                    BroadcastDelivery.broadcast_id == job.id, BroadcastDelivery.status == "queued"
                )
            )
            if not remaining:
                job.status = "completed"


async def run_worker(runtime):
    last_cleanup = None
    while True:
        try:
            if last_cleanup is None or (utcnow() - last_cleanup).total_seconds() >= 3600:
                await maintenance(runtime)
                last_cleanup = utcnow()
            _, delay = await deliver_one(runtime)
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("worker_iteration_failed")
            await asyncio.sleep(5)
