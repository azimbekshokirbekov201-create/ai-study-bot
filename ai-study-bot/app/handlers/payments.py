import secrets
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from app.bot.context import Runtime
from app.database.base import aware, utcnow
from app.keyboards import inline_menu
from app.localization import tr
from app.models import User
from app.payments.stars import TelegramStarsProvider
from app.payments.terms import payment_terms
from app.services.errors import PaymentRejected
from app.services.subscriptions import premium_until

router = Router(name="payments")


async def premium_navigation(message, dest, student, session, runtime):
    settings, lang = runtime.settings, student.language
    if dest == "premium:buy":
        nonce = secrets.token_hex(16)
        student.state = "payment_terms"
        student.state_data = {
            "nonce": nonce,
            "created_at": utcnow().isoformat(),
            "amount": settings.premium_stars,
            "days": settings.premium_days,
            "terms_version": settings.terms_version,
        }
        label = "✅ O‘qidim va roziman" if lang == "uz" else "✅ I have read and agree"
        return await message.answer(
            payment_terms(settings, lang),
            reply_markup=inline_menu([(label, f"nav:premium:confirm:{nonce}")], lang, "premium"),
        )
    if dest.startswith("premium:confirm:"):
        state = student.state_data
        valid = (
            student.state == "payment_terms"
            and dest.rsplit(":", 1)[1] == state.get("nonce")
            and state.get("amount") == settings.premium_stars
            and state.get("days") == settings.premium_days
            and state.get("terms_version") == settings.terms_version
        )
        if valid:
            valid = utcnow() - aware(datetime.fromisoformat(state["created_at"])) < timedelta(
                minutes=15
            )
        if not valid:
            return await message.answer(
                tr("stale", lang),
                reply_markup=inline_menu([(tr("buy", lang), "nav:premium:buy")], lang, "premium"),
            )
        provider = TelegramStarsProvider(settings)
        payment = await provider.create_invoice(
            session, student.id, terms_version=settings.terms_version, terms_accepted_at=utcnow()
        )
        student.state, student.state_data = "menu", {"nav": "premium"}
        description = (
            f"{settings.premium_days} kun Premium. Qabul qilingan shartlar: {settings.terms_version}."
            if lang == "uz"
            else f"{settings.premium_days} days of Premium. Accepted terms: {settings.terms_version}."
        )
        return await message.answer_invoice(
            title="AI Study Bot Premium",
            description=description,
            payload=payment.invoice_payload,
            currency="XTR",
            provider_token="",
            prices=[LabeledPrice(label="Premium", amount=payment.amount)],
        )
    expiry = await premium_until(session, student.id)
    if lang == "uz":
        text = (
            f"💎 Premium\n\nFree: kunlik test, {settings.ai_free_daily_requests} AI so‘rov/kun, asosiy tahlil.\n"
            f"Premium: {settings.ai_premium_daily_requests} AI so‘rov/kun, batafsil yozish tahlili, shaxsiy reja, to‘liq mavzu statistikasi va qo‘shimcha mashqlar.\n\n"
            "Audio yaratish va transkripsiya ham AI limitiga kiradi. Matn/audio budjetlari ham qo‘llanadi.\n"
            f"Narx: {settings.premium_stars} Stars / {settings.premium_days} kun. Avtomatik uzaytirish yo‘q.\n"
        )
    else:
        text = (
            f"💎 Premium\n\nFree: daily quiz, {settings.ai_free_daily_requests} AI requests/day, basic analytics.\n"
            f"Premium: {settings.ai_premium_daily_requests} AI requests/day, advanced writing feedback, personalized plans, full topic analytics and extra materials.\n\n"
            "Audio generation and transcription also count as AI requests. Content budgets also apply.\n"
            f"Price: {settings.premium_stars} Stars / {settings.premium_days} days. No automatic renewal.\n"
        )
    text += f"\n{'Premium until' if lang == 'en' else 'Premium muddati'}: {expiry.strftime('%Y-%m-%d %H:%M UTC') if expiry else 'Free'}"
    text += f"\n/paysupport: {settings.support_contact}"
    await message.answer(
        text,
        reply_markup=inline_menu(
            [
                (tr("buy", lang), "nav:premium:buy"),
                (tr("refresh", lang), "nav:premium"),
                (tr("terms", lang), "nav:terms"),
            ],
            lang,
        ),
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, student: User, session, runtime: Runtime):
    try:
        await TelegramStarsProvider(runtime.settings).validate_checkout(
            session, student.id, query.invoice_payload, query.currency, query.total_amount
        )
        await query.answer(ok=True)
    except PaymentRejected as exc:
        await query.answer(ok=False, error_message=str(exc)[:200])


@router.message(F.successful_payment)
async def successful_payment(message: Message, student: User, session, runtime: Runtime):
    receipt = message.successful_payment
    # Raising a mismatch rolls back and records an application error for review.
    await TelegramStarsProvider(runtime.settings).verify_success(
        session,
        student.id,
        receipt.invoice_payload,
        receipt.currency,
        receipt.total_amount,
        receipt.telegram_payment_charge_id,
    )
    await message.answer(
        "✅ Premium faollashtirildi. / Premium activated.",
        reply_markup=inline_menu([], student.language),
    )


@router.message(F.refunded_payment)
async def refunded_payment(message: Message, student: User, session, runtime: Runtime):
    receipt = message.refunded_payment
    await TelegramStarsProvider(runtime.settings).verify_refund(
        session,
        student.id,
        receipt.invoice_payload,
        receipt.currency,
        receipt.total_amount,
        receipt.telegram_payment_charge_id,
    )
    await message.answer(
        "To‘lov qaytarildi, tegishli obuna bekor qilindi. / Payment refunded; linked subscription revoked."
    )


@router.message(Command("paysupport", "support"))
async def payment_support(message: Message, runtime: Runtime):
    await message.answer(
        f"To‘lov bo‘yicha yordam / Payment support: {runtime.settings.support_contact}"
    )
