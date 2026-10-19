import secrets

from fastapi import Header, HTTPException, Request


def is_admin(telegram_id: int, settings) -> bool:
    return telegram_id in settings.admin_ids


async def require_admin(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_telegram_id: int | None = Header(default=None),
) -> str:
    settings = request.app.state.runtime.settings
    expected = settings.admin_api_token
    if expected is None:
        raise HTTPException(503, "Admin API is disabled")
    supplied = (authorization or "").removeprefix("Bearer ")
    if not secrets.compare_digest(supplied.encode(), expected.get_secret_value().encode()):
        raise HTTPException(401, "Unauthorized")
    if not is_admin(x_admin_telegram_id, settings):
        raise HTTPException(403, "Forbidden")
    return f"telegram:{x_admin_telegram_id}"
