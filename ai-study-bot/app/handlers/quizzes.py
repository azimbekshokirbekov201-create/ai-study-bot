from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.context import Runtime
from app.keyboards import inline_menu
from app.localization import tr
from app.models import User
from app.services.errors import UserError
from app.services.quizzes import QuizService

router = Router(name="quizzes")


async def show_question(message, attempt, service: QuizService, language: str):
    question = await service.current(attempt)
    if question is None:
        text = (
            f"Test: {attempt.status}\nTo‘g‘ri: {attempt.correct_count}/{attempt.question_count}\nBall: {attempt.points}"
            if language == "uz"
            else f"Quiz: {attempt.status}\nCorrect: {attempt.correct_count}/{attempt.question_count}\nPoints: {attempt.points}"
        )
        return await message.answer(text, reply_markup=inline_menu([], language))
    labels = "ABCD"
    text = f"{question.position + 1}/{attempt.question_count} · ⏳ {attempt.deadline:%H:%M:%S} UTC\n\n{question.prompt}\n\n"
    text += "\n".join(f"{labels[i]}. {option}" for i, option in enumerate(question.options))
    keyboard = inline_menu(
        [
            (label, f"ans:{attempt.id.hex}:{question.position}:{i}")
            for i, label in enumerate(labels)
        ],
        language,
        columns=4,
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("ans:"))
async def answer_callback(callback: CallbackQuery, student: User, session, runtime: Runtime):
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    try:
        _, attempt_id, position, option = callback.data.split(":")
        service = QuizService(session, runtime.settings)
        result = await service.answer(student.id, UUID(attempt_id), int(position), int(option))
    except (ValueError, UserError) as exc:
        return await callback.message.answer(
            str(exc) if isinstance(exc, UserError) else tr("stale", student.language)
        )
    if result.duplicate:
        await callback.message.answer("Bu javob saqlangan. / This answer was already saved.")
    elif result.expired:
        await callback.message.answer("⏳ Vaqt tugadi. / Time is up.")
    else:
        feedback = "✅" if result.correct else "❌"
        feedback += f" {'ABCD'[result.question.correct_option]} · +{result.points}\n{result.question.explanation}"
        await callback.message.answer(feedback)
    await show_question(callback.message, result.attempt, service, student.language)
