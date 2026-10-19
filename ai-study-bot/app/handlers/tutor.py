from io import BytesIO

from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import select

from app.bot.context import Runtime
from app.handlers.common import send_text
from app.keyboards import choices, inline_menu
from app.localization import tr
from app.models import Lesson, User
from app.services.analytics import statistics
from app.services.errors import UserError
from app.services.subscriptions import is_premium

router = Router(name="tutor")


async def tutor_navigation(message, dest, student, session, runtime):
    lang = student.language
    if dest == "tutor":
        return await message.answer(
            tr("tutor", lang),
            reply_markup=choices(
                ["ask", "correct", "exercise", "plan", "clear_history"], lang, "ai:"
            ),
        )
    if dest == "ai:clear_history":
        from app.handlers.navigation import navigate

        return await navigate(message, "clear_history", student, session, runtime)
    if not runtime.ai.available:
        return await message.answer(
            tr("ai_disabled", lang), reply_markup=inline_menu([], lang, "tutor")
        )
    mode = {
        "ai:ask": "tutor",
        "ai:correct": "correct",
        "ai:exercise": "exercise",
        "ai:plan": "plan",
    }.get(dest)
    context = ""
    lesson_id = None
    if dest.startswith("ai:lesson:"):
        try:
            lesson_id = int(dest.split(":")[2])
        except ValueError:
            return await message.answer(tr("stale", lang))
        lesson = await session.scalar(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.active.is_(True))
        )
        if not lesson:
            return await message.answer(tr("stale", lang))
        if lesson.premium_only and not await is_premium(session, student.id):
            return await message.answer(tr("premium_required", lang))
        context = getattr(lesson, f"body_{lang}")
        if lesson.topic == "listening":
            if not runtime.settings.tts_enabled:
                return await message.answer(
                    tr("listening_disabled", lang), reply_markup=inline_menu([], lang)
                )
            try:
                audio = await runtime.ai.speech(student, lesson.audio_script or "")
                await message.answer_audio(
                    BufferedInputFile(audio, filename="listening.mp3"),
                    caption="AI tomonidan yaratilgan ovoz / AI-generated voice",
                )
            except UserError as exc:
                return await message.answer(str(exc), reply_markup=inline_menu([], lang))
            mode = "listening"
            context += "\nReference script: " + (lesson.audio_script or "")
        elif lesson.topic.startswith("speaking"):
            mode = "speaking"
        elif lesson.topic.startswith("writing"):
            mode = "ielts_writing" if lesson.topic in ("writing1", "writing2") else "cefr_writing"
    if mode is None:
        return await message.answer(tr("stale", lang))
    if mode == "plan" and not await is_premium(session, student.id):
        return await message.answer(
            tr("premium_required", lang), reply_markup=choices(["premium"], lang, "")
        )
    student.state = "ai_input"
    student.state_data = {"nav": "tutor", "mode": mode, "context": context, "lesson_id": lesson_id}
    text = tr("ai_prompt", lang)
    if mode in ("speaking", "listening"):
        text += "\n" + (
            "Ovoz xabari: 2 daqiqagacha. Matndan talaffuzni ishonchli baholab bo‘lmaydi."
            if lang == "uz"
            else "Voice messages: up to 2 minutes. Pronunciation cannot be reliably assessed from text."
        )
    await message.answer(text, reply_markup=inline_menu([], lang, "tutor"))


async def handle_ai_message(message, student, session, runtime, text=None):
    try:
        mode = student.state_data.get("mode", "tutor")
        context = student.state_data.get("context", "")
        if mode == "plan":
            stats = await statistics(session, student.id)
            context = "Weak topics: " + ", ".join(
                f"{p.topic} {p.level}: {p.correct}/{p.answered}" for p in stats["progress"][:10]
            )
        response = await runtime.ai.respond(
            session, student, text or message.text or "", mode=mode, context=context
        )
        await send_text(message, response, inline_menu([], student.language, "tutor"))
    except UserError as exc:
        await message.answer(str(exc), reply_markup=inline_menu([], student.language, "tutor"))


@router.message(F.voice)
async def voice_message(message: Message, student: User, session, runtime: Runtime):
    if student.state != "ai_input" or student.state_data.get("mode") != "speaking":
        return await message.answer(
            tr("voice_disabled", student.language)
            if not runtime.settings.transcription_enabled
            else "Avval Speaking bo‘limini tanlang. / First open a Speaking lesson.",
            reply_markup=inline_menu([], student.language),
        )
    if not runtime.settings.transcription_enabled:
        return await message.answer(tr("voice_disabled", student.language))
    if message.voice.duration > 120 or (message.voice.file_size or 0) > 8 * 1024 * 1024:
        return await message.answer(
            "Ovoz chegarasi: 2 daqiqa, 8 MB. / Voice limit: 2 minutes, 8 MB."
        )
    buffer = BytesIO()
    try:
        await runtime.bot.download(message.voice, destination=buffer, timeout=20)
        text = await runtime.ai.transcribe(student, buffer.getvalue(), message.voice.duration)
        await send_text(message, "📝 " + text)
        await handle_ai_message(message, student, session, runtime, text=text)
    except UserError as exc:
        await message.answer(str(exc))


@router.message(F.text.func(lambda text: len(text) > 1000))
async def long_text(message: Message, student: User, session, runtime: Runtime):
    if student.state == "ai_input":
        await handle_ai_message(message, student, session, runtime)
    else:
        await message.answer(
            "Avval bo‘limni tanlang. / Open a section first.",
            reply_markup=inline_menu([], student.language),
        )
