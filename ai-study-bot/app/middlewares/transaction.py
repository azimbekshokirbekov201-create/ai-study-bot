import asyncio
import logging
from datetime import timedelta
from uuid import uuid4

from aiogram import BaseMiddleware
from aiogram.types import Update
from sqlalchemy import select

from app.bot.context import Runtime
from app.database.base import aware, utcnow
from app.database.session import advisory_lock
from app.localization import tr
from app.models import ApplicationError, UpdateReceipt, User
from app.repositories.users import register_user

logger = logging.getLogger(__name__)


class TransactionMiddleware(BaseMiddleware):
    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        # Leave pool capacity for independent AI reservations and fast checkout.
        self.slots = asyncio.Semaphore(8)

    async def __call__(self, handler, event: Update, data):
        if event.pre_checkout_query:
            try:
                async with asyncio.timeout(8):
                    return await self.process(handler, event, data)
            except Exception:
                logger.warning("checkout_processing_unavailable")
                await data["bot"].answer_pre_checkout_query(
                    pre_checkout_query_id=event.pre_checkout_query.id,
                    ok=False,
                    error_message="Please try again / Qayta urinib ko‘ring",
                    request_timeout=1,
                )
                return None
        async with self.slots:
            return await self.process(handler, event, data)

    async def process(self, handler, event: Update, data):
        message = event.message or (event.callback_query.message if event.callback_query else None)
        if message and message.chat.type != "private":
            if event.callback_query:
                await event.callback_query.answer("Open the bot in a private chat", show_alert=True)
            return None
        error_id = uuid4()
        try:
            async with self.runtime.database.sessions() as session, session.begin():
                await advisory_lock(session, 1, event.update_id)
                if await session.get(UpdateReceipt, event.update_id):
                    return None
                session.add(UpdateReceipt(update_id=event.update_id))
                telegram_user = data.get("event_from_user")
                user = None
                if telegram_user:
                    if event.pre_checkout_query:
                        # Do not wait for an in-flight tutor transaction's user lock.
                        user = await session.scalar(
                            select(User).where(User.telegram_id == telegram_user.id)
                        )
                        if not user:
                            await event.pre_checkout_query.answer(
                                ok=False, error_message="Open /start and create a new invoice"
                            )
                            return None
                    else:
                        user = await register_user(session, telegram_user)
                    # Payment updates must always be processed, even during a message burst.
                    financial = bool(
                        event.pre_checkout_query
                        or (
                            event.message
                            and (event.message.successful_payment or event.message.refunded_payment)
                        )
                    )
                    if not financial:
                        now = utcnow()
                        if now - aware(user.rate_window) >= timedelta(minutes=1):
                            user.rate_window, user.rate_count = now, 0
                        user.rate_count += 1
                        if user.rate_count > self.runtime.settings.rate_limit_per_minute:
                            if event.callback_query:
                                await event.callback_query.answer(
                                    tr("rate", user.language), show_alert=True
                                )
                            elif (
                                event.message
                                and user.rate_count
                                == self.runtime.settings.rate_limit_per_minute + 1
                            ):
                                await event.message.answer(tr("rate", user.language))
                            return None
                data.update(session=session, student=user, runtime=self.runtime)
                return await handler(event, data)
        except Exception as exc:
            logger.error("telegram_update_failed", exc_info=True)
            try:
                async with self.runtime.database.sessions() as session, session.begin():
                    session.add(
                        ApplicationError(
                            id=error_id,
                            error_type=type(exc).__name__[:100],
                            location="telegram_update",
                        )
                    )
                if event.message and event.message.chat.type == "private":
                    await event.message.answer(tr("error") + str(error_id))
            except Exception:
                logger.error("error_record_failed")
            raise
