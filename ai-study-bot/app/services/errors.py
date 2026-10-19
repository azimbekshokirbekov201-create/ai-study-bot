class UserError(Exception):
    """Expected, safe to show to a student. Never include provider exceptions."""


class QuotaExceeded(UserError):
    pass


class PaymentRejected(UserError):
    pass
