from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.database.base import utcnow
from app.models import Payment, Subscription, User
from app.payments.stars import TelegramStarsProvider
from app.services.errors import PaymentRejected
from app.services.subscriptions import grant_subscription, is_premium, premium_until


async def student(session):
    user = User(telegram_id=545, display_name="Buyer")
    session.add(user)
    await session.flush()
    return user


async def test_invoice_and_checkout_never_activate_premium(session, settings):
    user = await student(session)
    provider = TelegramStarsProvider(settings)
    payment = await provider.create_invoice(
        session, user.id, terms_version=settings.terms_version, terms_accepted_at=utcnow()
    )
    await provider.validate_checkout(
        session, user.id, payment.invoice_payload, "XTR", payment.amount
    )
    assert not await is_premium(session, user.id)
    for payer, currency, amount in [
        (999, "XTR", payment.amount),
        (user.id, "USD", payment.amount),
        (user.id, "XTR", 1),
    ]:
        with pytest.raises(PaymentRejected):
            await provider.verify_success(
                session, payer, payment.invoice_payload, currency, amount, "test-charge"
            )
    assert payment.status == "pending"


async def test_verified_payment_is_idempotent_and_refund_revokes(session, settings):
    user = await student(session)
    provider = TelegramStarsProvider(settings)
    payment = await provider.create_invoice(
        session, user.id, terms_version=settings.terms_version, terms_accepted_at=utcnow()
    )
    args = (session, user.id, payment.invoice_payload, "XTR", payment.amount, "test-only-charge")
    await provider.verify_success(*args)
    assert await is_premium(session, user.id)
    first_expiry = await premium_until(session, user.id)
    await provider.verify_success(*args)
    assert await premium_until(session, user.id) == first_expiry
    assert await session.scalar(select(func.count()).select_from(Subscription)) == 1
    await provider.verify_refund(*args)
    assert not await is_premium(session, user.id)
    assert payment.status == "refunded"
    with pytest.raises(PaymentRejected):
        await provider.verify_success(*args)


async def test_charge_cannot_pay_two_invoices(session, settings):
    user = await student(session)
    provider = TelegramStarsProvider(settings)
    first = await provider.create_invoice(
        session, user.id, terms_version=settings.terms_version, terms_accepted_at=utcnow()
    )
    await provider.verify_success(
        session, user.id, first.invoice_payload, "XTR", first.amount, "unique-test-charge"
    )
    second = await provider.create_invoice(
        session, user.id, terms_version=settings.terms_version, terms_accepted_at=utcnow()
    )
    with pytest.raises(PaymentRejected, match="already applied"):
        await provider.verify_success(
            session, user.id, second.invoice_payload, "XTR", second.amount, "unique-test-charge"
        )
    assert second.status == "pending"
    assert (
        await session.scalar(
            select(func.count()).select_from(Payment).where(Payment.status == "paid")
        )
        == 1
    )


async def test_subscription_expiration_and_renewal_intervals(session):
    user = await student(session)
    now = utcnow()
    session.add(
        Subscription(
            user_id=user.id, starts_at=now - timedelta(days=31), ends_at=now - timedelta(seconds=1)
        )
    )
    await session.flush()
    assert not await is_premium(session, user.id, now)
    first = await grant_subscription(session, user.id, 30)
    second = await grant_subscription(session, user.id, 30)
    assert first.ends_at == second.starts_at
    assert await premium_until(session, user.id) == second.ends_at
    first.revoked_at = utcnow()
    await session.flush()
    assert not await is_premium(
        session, user.id
    )  # A refunded interval cannot leak through renewal overlap.
