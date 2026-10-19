import httpx
from pydantic import SecretStr

from app.bot.context import Runtime
from app.main import create_app
from app.middlewares.body_limit import BodyLimitMiddleware


async def test_lifespan_health_and_disabled_webhook(database, settings):
    app = create_app(settings, runtime=Runtime(settings, database), start_bot=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/health/live")).status_code == 200
            assert (await client.get("/health/ready")).status_code == 200
            assert (await client.post("/telegram/webhook", json={})).status_code == 503
            assert (await client.get("/admin/dashboard")).status_code == 503


async def test_webhook_rejects_untrusted_requests_before_processing(database, settings):
    cfg = settings.model_copy(
        update={
            "bot_mode": "webhook",
            "webhook_secret": SecretStr("test-only-webhook-secret-32-characters"),
        }
    )
    runtime = Runtime(cfg, database, bot=object(), ready=True)
    app = create_app(cfg, runtime=runtime, start_bot=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.post("/telegram/webhook", json={"update_id": 1})).status_code == 403
        response = await client.post(
            "/telegram/webhook",
            content="invalid",
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-only-webhook-secret-32-characters"},
        )
        assert response.status_code == 422


async def test_chunked_body_limit_rejects_without_calling_application():
    messages = [
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"5678", "more_body": False},
    ]
    sent = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    async def should_not_run(scope, receive, send):
        raise AssertionError("Oversized request reached the application")

    await BodyLimitMiddleware(should_not_run, max_bytes=5)({"type": "http"}, receive, send)
    assert sent[0]["status"] == 413
