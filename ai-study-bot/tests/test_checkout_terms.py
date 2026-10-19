import asyncio

import pytest
from aiogram.types import Update
from sqlalchemy import func, select

from app.database.base import utcnow
from app.database.session import advisory_lock
from app.models import Payment, User
from app.payments.stars import TelegramStarsProvider
from app.services.errors import PaymentRejected
from tests.telegram import callback_update, message_update
from tests.test_handlers import setup


async def test_invoice_creation_requires_explicit_current_terms(session, settings):
    provider = TelegramStarsProvider(settings)
    with pytest.raises(PaymentRejected, match="Accept the terms"):
        await provider.create_invoice(session, 1, terms_version="old", terms_accepted_at=utcnow())
    with pytest.raises(PaymentRejected, match="Accept the terms"):
        await provider.create_invoice(
            session, 1, terms_version=settings.terms_version, terms_accepted_at=None
        )


async def test_purchase_confirmation_cannot_be_forged_or_replayed(database, settings):
    dispatcher, bot, transport, runtime = await setup(database, settings)
    for data in [
        message_update(1, "/start"),
        callback_update(2, "nav:premium:confirm:forged"),
        callback_update(3, "nav:premium:buy"),
    ]:
        await dispatcher.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    confirmation = transport.calls[-1].reply_markup.inline_keyboard[0][0].callback_data
    for update_id in (4, 5):
        await dispatcher.feed_update(
            bot,
            Update.model_validate(callback_update(update_id, confirmation), context={"bot": bot}),
        )
    assert len([call for call in transport.calls if call.__api_method__ == "sendInvoice"]) == 1
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Payment)) == 1
        assert (await session.scalar(select(Payment))).terms_version == settings.terms_version
    await runtime.ai.close()


async def test_checkout_does_not_wait_for_inflight_student_ai_transaction(database, settings):
    if database.engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL advisory locks")
    dispatcher, bot, transport, runtime = await setup(database, settings)
    await dispatcher.feed_update(
        bot, Update.model_validate(message_update(1, "/start"), context={"bot": bot})
    )
    async with database.sessions() as session, session.begin():
        user = await session.scalar(select(User).where(User.telegram_id == 101))
        payment = await TelegramStarsProvider(settings).create_invoice(
            session, user.id, terms_version=settings.terms_version, terms_accepted_at=utcnow()
        )
    # Hold exactly the advisory lock an ongoing ordinary update owns.
    async with database.sessions() as busy_session, busy_session.begin():
        await advisory_lock(busy_session, 2, 101)
        body = {
            "update_id": 9,
            "pre_checkout_query": {
                "id": "fast-checkout",
                "from": {"id": 101, "is_bot": False, "first_name": "Student"},
                "currency": "XTR",
                "total_amount": payment.amount,
                "invoice_payload": payment.invoice_payload,
            },
        }
        async with asyncio.timeout(2):
            await dispatcher.feed_update(bot, Update.model_validate(body, context={"bot": bot}))
    assert transport.calls[-1].ok is True
    await runtime.ai.close()
