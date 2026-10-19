import asyncio

import httpx
from aiogram import Bot
from pydantic import SecretStr
from sqlalchemy import func, select

import app.main as main
from app.bot.context import Runtime
from app.models import UpdateReceipt, User
from tests.telegram import RecordingSession, message_update


async def test_polling_startup_readiness_and_shutdown(database, settings, monkeypatch):
    transport = RecordingSession()
    bot = Bot("123456:TEST_ONLY_TOKEN", session=transport)
    monkeypatch.setattr(main, "Bot", lambda *args, **kwargs: bot)
    # Avoid constructing an unused aiohttp session when the Bot factory is replaced.
    monkeypatch.setattr(main, "AiohttpSession", lambda **kwargs: None)
    cfg = settings.model_copy(update={"bot_token": SecretStr("123456:TEST_ONLY_TOKEN")})
    runtime = Runtime(cfg, database)
    app = main.create_app(cfg, runtime=runtime)
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/health/ready")).status_code == 200
        assert not runtime.polling_task.done()
    assert runtime.polling_task.done() and not runtime.ready
    assert any(call.__api_method__ == "deleteWebhook" for call in transport.calls)


async def test_authenticated_webhook_processes_and_deduplicates_update(
    database, settings, monkeypatch
):
    transport = RecordingSession()
    bot = Bot("123456:TEST_ONLY_TOKEN", session=transport)
    monkeypatch.setattr(main, "Bot", lambda *args, **kwargs: bot)
    monkeypatch.setattr(main, "AiohttpSession", lambda **kwargs: None)
    secret = "test-only-webhook-secret-32-characters"
    cfg = settings.model_copy(
        update={
            "bot_token": SecretStr("123456:TEST_ONLY_TOKEN"),
            "bot_mode": "webhook",
            "webhook_secret": SecretStr(secret),
            "public_base_url": "https://test.example",
        }
    )
    runtime = Runtime(cfg, database)
    app = main.create_app(cfg, runtime=runtime)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            headers = {"X-Telegram-Bot-Api-Secret-Token": secret}
            body = message_update(901, "/start")
            assert (
                await client.post(cfg.webhook_path, json=body, headers=headers)
            ).status_code == 200
            call_count = len([c for c in transport.calls if c.__api_method__ == "sendMessage"])
            assert (
                await client.post(cfg.webhook_path, json=body, headers=headers)
            ).status_code == 200
            assert (
                len([c for c in transport.calls if c.__api_method__ == "sendMessage"]) == call_count
            )
        async with database.sessions() as session:
            assert await session.scalar(select(func.count()).select_from(User)) == 1
            assert await session.scalar(select(func.count()).select_from(UpdateReceipt)) == 1
    webhook = next(c for c in transport.calls if c.__api_method__ == "setWebhook")
    assert webhook.secret_token == secret and not webhook.drop_pending_updates
