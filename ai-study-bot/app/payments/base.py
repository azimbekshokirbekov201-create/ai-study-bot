from typing import Protocol


class PaymentProvider(Protocol):
    async def create_invoice(
        self, session, user_id: int, *, terms_version: str, terms_accepted_at
    ): ...
    async def validate_checkout(
        self, session, user_id: int, payload: str, currency: str, amount: int
    ): ...
    async def verify_success(
        self, session, user_id: int, payload: str, currency: str, amount: int, charge_id: str
    ): ...
