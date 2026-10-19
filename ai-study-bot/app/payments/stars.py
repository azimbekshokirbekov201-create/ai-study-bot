import secrets
from datetime import timedelta

from sqlalchemy import select

from app.database.base import aware, utcnow
from app.database.session import advisory_lock
from app.models import Payment, Subscription
from app.services.errors import PaymentRejected
from app.services.subscriptions import grant_subscription


class TelegramStarsProvider:
    """Only call verification from authenticated Telegram updates / Bot API refunds.

    No client-facing endpoint is allowed to mark an invoice paid. XTR is used for
    digital subscriptions inside Telegram; no external card checkout is offered.
    """

    def __init__(self, settings):
        self.settings = settings

    async def create_invoice(self, session, user_id: int, *, terms_version, terms_accepted_at):
        if not terms_accepted_at or terms_version != self.settings.terms_version:
            raise PaymentRejected("Avval shartlarga rozilik bildiring. / Accept the terms first.")
        payment = Payment(
            user_id=user_id,
            invoice_payload=secrets.token_urlsafe(32),
            currency="XTR",
            amount=self.settings.premium_stars,
            duration_days=self.settings.premium_days,
            terms_version=terms_version,
            terms_accepted_at=terms_accepted_at,
        )
        session.add(payment)
        await session.flush()
        return payment

    async def find(self, session, user_id, payload, currency, amount):
        payment = await session.scalar(
            select(Payment).where(Payment.invoice_payload == payload).with_for_update()
        )
        if (
            not payment
            or payment.user_id != user_id
            or payment.provider != "telegram_stars"
            or currency != "XTR"
            or payment.currency != currency
            or payment.amount != amount
        ):
            raise PaymentRejected(
                "To‘lov ma’lumotlari mos kelmadi. / Payment details did not match the invoice."
            )
        return payment

    async def validate_checkout(self, session, user_id, payload, currency, amount):
        payment = await self.find(session, user_id, payload, currency, amount)
        if (
            not payment.terms_accepted_at
            or payment.status != "pending"
            or utcnow() - aware(payment.created_at) > timedelta(hours=24)
        ):
            raise PaymentRejected(
                "Hisob muddati tugagan. Yangisini yarating. / Invoice expired; create a new one."
            )
        return payment

    async def verify_success(self, session, user_id, payload, currency, amount, charge_id):
        await advisory_lock(session, 5, user_id)
        payment = await self.find(session, user_id, payload, currency, amount)
        if not charge_id or len(charge_id) > 256:
            raise PaymentRejected("Noto‘g‘ri to‘lov raqami. / Invalid charge ID.")
        if payment.status == "paid" and payment.provider_charge_id == charge_id:
            return payment
        if payment.status != "pending":
            raise PaymentRejected("To‘lov holati mos emas. / Invalid payment state.")
        existing = await session.scalar(
            select(Payment.id).where(Payment.provider_charge_id == charge_id)
        )
        if existing is not None:
            raise PaymentRejected("To‘lov allaqachon ishlatilgan. / Charge already applied.")
        payment.status, payment.provider_charge_id, payment.paid_at = "paid", charge_id, utcnow()
        await grant_subscription(
            session, user_id, payment.duration_days, payment_id=payment.id, source="payment"
        )
        return payment

    async def verify_refund(self, session, user_id, payload, currency, amount, charge_id):
        await advisory_lock(session, 5, user_id)
        payment = await self.find(session, user_id, payload, currency, amount)
        if payment.provider_charge_id != charge_id or payment.status not in ("paid", "refunded"):
            raise PaymentRejected(
                "Qaytarish ma’lumotlari mos emas. / Refund did not match a paid charge."
            )
        payment.status = "refunded"
        subscription = await session.scalar(
            select(Subscription).where(Subscription.payment_id == payment.id).with_for_update()
        )
        if subscription and not subscription.revoked_at:
            subscription.revoked_at = utcnow()
        return payment
