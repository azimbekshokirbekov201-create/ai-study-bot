from aiogram import Bot
from aiogram.types import Update
from sqlalchemy import func, select

from app.ai.tutor import TutorService
from app.bot.context import Runtime
from app.bot.dispatcher import create_dispatcher
from app.localization import MAIN_ITEMS, tr
from app.models import Payment, QuizAttempt, Subscription, UpdateReceipt, User
from app.services.catalog import lessons
from scripts.seed import seed
from tests.telegram import RecordingSession, callback_update, message_update


async def setup(database, settings):
    cfg = settings.model_copy(update={"rate_limit_per_minute": 300})
    transport = RecordingSession()
    bot = Bot("123456:TEST_ONLY_TOKEN", session=transport)
    runtime = Runtime(cfg, database, ai=TutorService(database, cfg), bot=bot)
    async with database.sessions() as session, session.begin():
        await seed(session)
    return create_dispatcher(runtime), bot, transport, runtime


async def test_every_main_menu_and_curriculum_navigation_dispatches(database, settings):
    dispatcher, bot, transport, runtime = await setup(database, settings)
    update_id = 0

    async def feed(data):
        await dispatcher.feed_update(bot, Update.model_validate(data, context={"bot": bot}))

    await feed(message_update(update_id, "/start"))
    for key in MAIN_ITEMS:
        update_id += 1
        await feed(message_update(update_id, tr(key, "uz")))
    for spec in lessons():
        update_id += 1
        dest = (
            f"learn:{spec.subject}:{spec.level}:{spec.topic}"
            if spec.level
            else f"learn:{spec.subject}:{spec.topic}"
        )
        await feed(callback_update(update_id, "nav:" + dest))
    for dest in [
        "level:A1",
        "level:A2",
        "level:B1",
        "level:B2",
        "level:C1",
        "sat:math",
        "sat:rw",
        "settings",
        "language",
        "lang:en",
        "profile",
        "statistics",
        "leaderboard:day",
        "leaderboard:week",
        "leaderboard:month",
        "leaderboard:all",
        "tutor",
        "ai:ask",
        "premium",
        "privacy",
        "terms",
        "home",
    ]:
        update_id += 1
        await feed(callback_update(update_id, "nav:" + dest))
    sent = [call for call in transport.calls if call.__api_method__ == "sendMessage"]
    assert len(sent) >= 70
    assert any(call.text == tr("ai_disabled", "en") for call in sent)
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(UpdateReceipt)) == update_id + 1
        )
    await runtime.ai.close()


async def test_duplicate_updates_and_unauthorized_admin_callbacks(database, settings):
    dispatcher, bot, transport, runtime = await setup(database, settings)
    update = Update.model_validate(message_update(1, "/start"), context={"bot": bot})
    await dispatcher.feed_update(bot, update)
    calls = len(transport.calls)
    await dispatcher.feed_update(bot, update)
    assert len(transport.calls) == calls
    await dispatcher.feed_update(
        bot, Update.model_validate(callback_update(2, "adm:dashboard"), context={"bot": bot})
    )
    assert transport.calls[-1].text == "Access denied"
    await runtime.ai.close()


async def test_stars_invoice_to_verified_payment_through_actual_handlers(database, settings):
    dispatcher, bot, transport, runtime = await setup(database, settings)
    for data in [message_update(1, "/start"), callback_update(2, "nav:premium:buy")]:
        await dispatcher.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    assert not any(call.__api_method__ == "sendInvoice" for call in transport.calls)
    confirmation = transport.calls[-1].reply_markup.inline_keyboard[0][0].callback_data
    await dispatcher.feed_update(
        bot, Update.model_validate(callback_update(20, confirmation), context={"bot": bot})
    )
    invoice = next(call for call in transport.calls if call.__api_method__ == "sendInvoice")
    assert invoice.currency == "XTR" and invoice.provider_token == ""
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Subscription)) == 0
    checkout = {
        "update_id": 3,
        "pre_checkout_query": {
            "id": "checkout-test",
            "from": {"id": 101, "is_bot": False, "first_name": "Aziza"},
            "currency": "XTR",
            "total_amount": invoice.prices[0].amount,
            "invoice_payload": invoice.payload,
        },
    }
    await dispatcher.feed_update(bot, Update.model_validate(checkout, context={"bot": bot}))
    assert transport.calls[-1].ok is True
    data = message_update(
        4,
        "",
        successful_payment={
            "currency": "XTR",
            "total_amount": invoice.prices[0].amount,
            "invoice_payload": invoice.payload,
            "telegram_payment_charge_id": "offline-test-charge",
            "provider_payment_charge_id": "",
        },
    )
    await dispatcher.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    async with database.sessions() as session:
        assert (await session.scalar(select(Payment))).status == "paid"
        assert (await session.scalar(select(Payment))).terms_accepted_at is not None
        assert await session.scalar(select(func.count()).select_from(Subscription)) == 1
    await runtime.ai.close()


async def test_quiz_callbacks_work_after_navigation(database, settings):
    dispatcher, bot, transport, runtime = await setup(database, settings)
    for data in [
        message_update(1, "/start"),
        callback_update(2, "nav:difficulty:sat_math:_:algebra"),
        callback_update(3, "nav:quiz:sat_math:_:algebra:1"),
    ]:
        await dispatcher.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    question = transport.calls[-1]
    callback = question.reply_markup.inline_keyboard[0][1].callback_data
    await dispatcher.feed_update(
        bot, Update.model_validate(callback_update(4, callback), context={"bot": bot})
    )
    async with database.sessions() as session:
        attempt = await session.scalar(select(QuizAttempt))
        assert attempt.correct_count == 1
    await runtime.ai.close()
