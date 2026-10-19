import json
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from pydantic import ValidationError
from sqlalchemy import select

from app.admin.schemas import QuestionInput
from app.admin.security import is_admin
from app.admin.service import (
    audit,
    dashboard,
    grant_premium,
    queue_broadcast,
    revoke_premium,
    save_question,
)
from app.bot.context import Runtime
from app.handlers.common import send_text
from app.keyboards import inline_menu
from app.models import ApplicationError, Payment, Question, User
from app.services.errors import UserError

router = Router(name="admin")


def admin_keyboard(language):
    return inline_menu(
        [
            ("📊 Dashboard", "adm:dashboard"),
            ("💳 Payments", "adm:payments"),
            ("📚 Content / Premium", "adm:content"),
            ("⚠️ Errors", "adm:errors"),
        ],
        language,
    )


@router.message(Command("admin", "qadd", "qedit", "qdelete", "grant", "revoke", "broadcast"))
async def admin_command(
    message: Message, command: CommandObject, student: User, session, runtime: Runtime
):
    if not is_admin(student.telegram_id, runtime.settings):
        return await message.answer("⛔ Ruxsat yo‘q. / Access denied.")
    actor = f"telegram:{student.telegram_id}"
    args = command.args or ""
    try:
        if command.command == "admin":
            stats = await dashboard(session)
            return await message.answer(
                "Admin\n" + "\n".join(f"{k}: {v}" for k, v in stats.items()),
                reply_markup=admin_keyboard(student.language),
            )
        if command.command == "qadd":
            row = await save_question(session, QuestionInput.model_validate_json(args), actor)
            return await message.answer(f"Question {row.id} created")
        if command.command == "qedit":
            row_id, body = args.split(maxsplit=1)
            row = await save_question(
                session, QuestionInput.model_validate_json(body), actor, int(row_id)
            )
            return await message.answer(f"Question {row.id} updated")
        if command.command == "qdelete":
            row = await session.get(Question, int(args), with_for_update=True)
            if not row:
                raise UserError("Question not found")
            row.active = False
            audit(session, actor, "question.deactivate", row.id)
            return await message.answer("Question deactivated; history preserved")
        if command.command == "grant":
            telegram_id, days, reason = args.split(maxsplit=2)
            if not 1 <= int(days) <= 366 or not 5 <= len(reason) <= 500:
                raise ValueError
            row = await grant_premium(session, int(telegram_id), int(days), actor, reason)
            return await message.answer(f"Premium until {row.ends_at:%Y-%m-%d %H:%M} UTC")
        if command.command == "revoke":
            telegram_id, reason = args.split(maxsplit=1)
            if len(reason) < 5:
                raise ValueError
            await revoke_premium(session, int(telegram_id), actor, reason[:500])
            return await message.answer("Subscriptions revoked")
        if command.command == "broadcast":
            if not 1 <= len(args) <= 3500:
                raise ValueError
            nonce = uuid4().hex
            student.state, student.state_data = "admin_broadcast", {"text": args, "nonce": nonce}
            return await send_text(
                message,
                "Broadcast preview:\n\n" + args,
                inline_menu([("Confirm broadcast", f"adm:send:{nonce}")], student.language),
            )
    except (ValueError, ValidationError):
        await message.answer(
            "Invalid input. /admin shows command syntax and the Admin API supports full JSON payloads."
        )
    except UserError as exc:
        await message.answer(str(exc))


@router.callback_query(F.data.startswith("adm:"))
async def admin_callback(callback: CallbackQuery, student: User, session, runtime: Runtime):
    if not is_admin(student.telegram_id, runtime.settings):
        return await callback.answer("Access denied", show_alert=True)
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    dest = callback.data[4:]
    if dest == "dashboard":
        stats = await dashboard(session)
        return await callback.message.answer(
            json.dumps(stats, indent=2), reply_markup=admin_keyboard(student.language)
        )
    if dest == "payments":
        rows = (
            await session.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(10))
        ).all()
        return await callback.message.answer(
            "\n".join(f"{p.id} · user {p.user_id} · {p.amount} XTR · {p.status}" for p in rows)
            or "No payments"
        )
    if dest == "errors":
        rows = (
            await session.scalars(
                select(ApplicationError).order_by(ApplicationError.created_at.desc()).limit(10)
            )
        ).all()
        return await callback.message.answer(
            "\n".join(f"{e.id} · {e.error_type} · {e.location}" for e in rows) or "No errors"
        )
    if dest == "content":
        return await callback.message.answer(
            "Commands:\n/qadd JSON\n/qedit ID JSON\n/qdelete ID\n/grant TELEGRAM_ID DAYS REASON\n/revoke TELEGRAM_ID REASON\n/broadcast TEXT\n\nFull question, subject and lesson management: authenticated /admin API. See README and /openapi.json when enabled."
        )
    if dest.startswith("send:"):
        if student.state != "admin_broadcast" or dest[5:] != student.state_data.get("nonce"):
            return await callback.message.answer("This preview has expired")
        job = await queue_broadcast(
            session, student.state_data["text"], f"telegram:{student.telegram_id}"
        )
        student.state, student.state_data = "menu", {}
        await callback.message.answer(f"Broadcast queued: {job.id}")
