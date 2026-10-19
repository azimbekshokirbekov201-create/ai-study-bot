import asyncio
import contextlib
import json
import logging
import secrets
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand, Update
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import __version__
from app.admin.api import router as admin_router
from app.admin.security import require_admin
from app.ai.tutor import TutorService
from app.bot.context import Runtime
from app.bot.dispatcher import ALLOWED_UPDATES, create_dispatcher
from app.config import get_settings
from app.config.logging import configure_logging
from app.database import Database
from app.middlewares.body_limit import BodyLimitMiddleware
from app.models import UpdateReceipt
from app.services.errors import UserError
from app.services.worker import run_worker

logger = logging.getLogger(__name__)


def create_app(settings=None, *, runtime=None, start_bot=True):
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    runtime = runtime or Runtime(settings, Database(settings))

    @asynccontextmanager
    async def lifespan(application):
        try:
            await runtime.database.healthy()
            if start_bot:
                async with runtime.database.sessions() as session:
                    await session.scalar(select(UpdateReceipt.update_id).limit(1))
            runtime.ai = runtime.ai or TutorService(runtime.database, settings)
            if settings.redis_url:
                runtime.redis = Redis.from_url(
                    settings.redis_url.get_secret_value(),
                    decode_responses=True,
                    socket_timeout=3,
                    socket_connect_timeout=3,
                    max_connections=20,
                )
                await runtime.redis.ping()
            if start_bot and settings.bot_token:
                runtime.bot = Bot(
                    settings.bot_token.get_secret_value(), session=AiohttpSession(timeout=60)
                )
                dispatcher = create_dispatcher(runtime)
                application.state.dispatcher = dispatcher
                await runtime.bot.get_me()
                await runtime.bot.set_my_commands(
                    [
                        BotCommand(command="start", description="Bosh menyu / Main menu"),
                        BotCommand(command="cancel", description="Bekor qilish / Cancel"),
                        BotCommand(command="privacy", description="Maxfiylik / Privacy"),
                        BotCommand(command="terms", description="Shartlar / Terms"),
                        BotCommand(
                            command="paysupport", description="To‘lov yordami / Payment support"
                        ),
                    ]
                )
                if settings.bot_mode == "webhook":
                    await runtime.bot.set_webhook(
                        url=settings.public_base_url.rstrip("/") + settings.webhook_path,
                        secret_token=settings.webhook_secret.get_secret_value(),
                        allowed_updates=ALLOWED_UPDATES,
                        max_connections=20,
                        drop_pending_updates=False,
                    )
                else:
                    await runtime.bot.delete_webhook(drop_pending_updates=False)
                    runtime.polling_task = asyncio.create_task(
                        dispatcher.start_polling(
                            runtime.bot,
                            allowed_updates=ALLOWED_UPDATES,
                            handle_signals=False,
                            close_bot_session=False,
                            tasks_concurrency_limit=100,
                        ),
                        name="telegram-polling",
                    )
                runtime.worker_task = asyncio.create_task(
                    run_worker(runtime), name="maintenance-broadcasts"
                )
                runtime.ready = True
            elif not start_bot:
                runtime.ready = True
            else:
                logger.warning("bot_disabled_missing_token")
            yield
        finally:
            runtime.ready = False
            if runtime.polling_task:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(application.state.dispatcher.stop_polling(), timeout=10)
            for task in (runtime.polling_task, runtime.worker_task):
                if task:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await task
            if runtime.bot:
                await runtime.bot.session.close()
            if runtime.ai:
                await runtime.ai.close()
            if runtime.redis:
                await runtime.redis.aclose()
            await runtime.database.close()

    application = FastAPI(
        title="AI Study Bot",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.runtime = runtime
    application.state.webhook_slots = asyncio.Semaphore(20)
    application.include_router(admin_router)

    @application.exception_handler(UserError)
    async def expected_error(_request, exc):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(IntegrityError)
    async def integrity_error(_request, _exc):
        return JSONResponse(status_code=409, content={"detail": "Data conflict; reload and retry"})

    @application.middleware("http")
    async def http_limits(request, call_next):
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 1024 * 1024:
            return JSONResponse(status_code=413, content={"detail": "Request too large"})
        if request.url.path.startswith("/admin") and runtime.redis:
            # Only the direct peer is trusted; X-Forwarded-For is not accepted here.
            peer = request.client.host if request.client else "unknown"
            from app.database.base import utcnow

            key = f"http-rate:{peer}:{int(utcnow().timestamp()) // 60}"
            result = await runtime.redis.eval(
                "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],61) end; return n",
                1,
                key,
            )
            if result > 120:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health/live")
    async def live():
        return {"status": "alive", "version": __version__}

    @application.get("/health/ready")
    async def ready():
        try:
            await runtime.database.healthy()
            if runtime.redis:
                await runtime.redis.ping()
            polling_ok = not runtime.polling_task or not runtime.polling_task.done()
            if not runtime.ready or not polling_ok:
                raise RuntimeError("Bot not ready")
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @application.get(
        "/openapi.json", dependencies=[Depends(require_admin)], include_in_schema=False
    )
    async def schema():
        return get_openapi(
            title=application.title, version=application.version, routes=application.routes
        )

    async def webhook(request: Request):
        if settings.bot_mode != "webhook" or not runtime.ready or not runtime.bot:
            raise HTTPException(503, "Webhook is not active")
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secrets.compare_digest(
            supplied.encode(), settings.webhook_secret.get_secret_value().encode()
        ):
            raise HTTPException(403, "Forbidden")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024 * 1024:
                raise HTTPException(413, "Request too large")
        try:
            update = Update.model_validate(json.loads(raw), context={"bot": runtime.bot})
        except (ValueError, ValidationError):
            raise HTTPException(422, "Invalid Telegram update") from None
        try:
            if update.pre_checkout_query:
                await application.state.dispatcher.feed_update(runtime.bot, update)
            else:
                async with application.state.webhook_slots:
                    await application.state.dispatcher.feed_update(runtime.bot, update)
        except Exception:
            logger.error("webhook_update_failed")
            raise HTTPException(503, "Update processing failed; retry") from None
        return {"ok": True}

    application.add_api_route(
        settings.webhook_path, webhook, methods=["POST"], include_in_schema=False
    )
    application.add_middleware(BodyLimitMiddleware)
    return application


app = create_app()
