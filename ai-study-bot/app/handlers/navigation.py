from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete

from app.bot.context import Runtime
from app.handlers.common import send_text
from app.keyboards import choices, inline_menu, main_menu
from app.localization import menu_key, tr
from app.models import AIConversation, User

router = Router(name="navigation")


async def home(message: Message, student: User):
    student.state, student.state_data = "menu", {"nav": "home"}
    await message.answer(tr("welcome", student.language), reply_markup=main_menu(student.language))


async def navigate(message: Message, dest: str, student: User, session, runtime: Runtime):
    lang = student.language
    previous = student.state_data.get("nav", "home")
    # Preserve the single-use terms preview until its confirmation is validated.
    if not dest.startswith("premium:confirm:"):
        student.state, student.state_data = "menu", {"nav": dest, "previous": previous}
    if dest == "home":
        return await home(message, student)
    if dest == "ielts":
        return await message.answer(
            tr("ielts", lang),
            reply_markup=choices(
                [
                    "listening",
                    "reading",
                    "writing1",
                    "writing2",
                    "speaking1",
                    "speaking2",
                    "speaking3",
                    "vocabulary",
                    "grammar",
                ],
                lang,
                "learn:ielts:",
                columns=2,
            ),
        )
    if dest == "cefr":
        return await message.answer(
            "CEFR — A1 / A2 / B1 / B2 / C1",
            reply_markup=inline_menu(
                [
                    (f"{'✓ ' if student.cefr_level == level else ''}{level}", f"nav:level:{level}")
                    for level in ("A1", "A2", "B1", "B2", "C1")
                ],
                lang,
                columns=3,
            ),
        )
    if dest.startswith("level:"):
        level = dest.split(":")[1]
        if level not in ("A1", "A2", "B1", "B2", "C1"):
            return await home(message, student)
        student.cefr_level = level
        return await message.answer(
            f"CEFR {level}",
            reply_markup=choices(
                ["listening", "reading", "writing", "speaking", "grammar", "vocabulary"],
                lang,
                f"learn:cefr:{level}:",
                "cefr",
                2,
            ),
        )
    if dest == "sat":
        return await message.answer(
            tr("sat", lang), reply_markup=choices(["math", "rw"], lang, "sat:", columns=2)
        )
    if dest in ("sat:math", "sat:rw"):
        keys = (
            ["algebra", "advanced_math", "data_analysis", "geometry"]
            if dest.endswith("math")
            else [
                "vocabulary_context",
                "grammar",
                "transitions",
                "main_ideas",
                "inference",
                "rhetorical_synthesis",
            ]
        )
        subject = "sat_math" if dest.endswith("math") else "sat_rw"
        return await message.answer(
            tr("sat", lang), reply_markup=choices(keys, lang, f"learn:{subject}:", "sat")
        )
    if dest == "settings":
        return await message.answer(
            tr("settings", lang),
            reply_markup=choices(
                ["language", "goals", "announcements", "clear_history", "privacy", "terms"],
                lang,
                "",
            ),
        )
    if dest == "language":
        return await message.answer(
            "Til / Language",
            reply_markup=inline_menu(
                [("🇺🇿 O‘zbekcha", "nav:lang:uz"), ("🇬🇧 English", "nav:lang:en")],
                lang,
                "settings",
                2,
            ),
        )
    if dest in ("lang:uz", "lang:en"):
        student.language = dest.split(":")[1]
        return await home(message, student)
    if dest == "goals":
        student.state = "goals"
        return await message.answer(
            tr("goals_prompt", lang), reply_markup=inline_menu([], lang, "profile")
        )
    if dest == "announcements":
        student.announcements_enabled = not student.announcements_enabled
        return await message.answer(
            f"{tr('saved', lang)} 🔔 {'ON' if student.announcements_enabled else 'OFF'}",
            reply_markup=inline_menu([], lang, "settings"),
        )
    if dest == "clear_history":
        await session.execute(delete(AIConversation).where(AIConversation.user_id == student.id))
        return await message.answer(
            tr("saved", lang), reply_markup=inline_menu([], lang, "settings")
        )
    if dest == "privacy":
        text = (
            (
                "We store your Telegram ID, profile, study results, subscription/payment records and AI conversation text. "
                "AI submissions are sent to OpenAI; voice submissions are sent only when transcription is enabled. "
                f"AI history retention: {runtime.settings.ai_history_retention_days} days. You can clear it in Settings. "
                f"For data export/deletion: {runtime.settings.privacy_contact}. Payment/audit records may need legal retention."
            )
            if lang == "en"
            else (
                "Telegram ID, profil, test natijalari, obuna/to‘lov yozuvlari va AI suhbat matnlari saqlanadi. "
                "AI ga yuborilgan matn OpenAI ga uzatiladi; ovoz faqat transkripsiya yoqilganida uzatiladi. "
                f"AI tarixi {runtime.settings.ai_history_retention_days} kun saqlanadi. Sozlamalarda tarixni o‘chirishingiz mumkin. "
                f"Ma’lumot nusxasi/o‘chirish: {runtime.settings.privacy_contact}. To‘lov/audit yozuvlari qonun talabi bilan saqlanishi mumkin."
            )
        )
        return await send_text(message, text, inline_menu([], lang, "settings"))
    if dest == "terms":
        from app.payments.terms import payment_terms

        return await send_text(
            message, payment_terms(runtime.settings, lang), inline_menu([], lang, "premium")
        )
    # Feature modules are imported lazily to avoid cyclic router dependencies.
    if dest.startswith(("learn:", "difficulty:", "quiz:", "competition:")) or dest == "daily":
        from app.handlers.learning import learning_navigation

        return await learning_navigation(message, dest, student, session, runtime)
    if dest in ("profile", "statistics") or dest.startswith("leaderboard"):
        from app.handlers.statistics import statistics_navigation

        return await statistics_navigation(message, dest, student, session, runtime)
    if dest == "tutor" or dest.startswith("ai:"):
        from app.handlers.tutor import tutor_navigation

        return await tutor_navigation(message, dest, student, session, runtime)
    if dest == "premium" or dest.startswith("premium:"):
        from app.handlers.payments import premium_navigation

        return await premium_navigation(message, dest, student, session, runtime)
    return await message.answer(tr("stale", lang), reply_markup=inline_menu([], lang))


@router.message(CommandStart())
@router.message(Command("menu", "cancel"))
async def start(message: Message, student: User):
    await home(message, student)


@router.message(Command("privacy", "terms"))
async def legal(message: Message, student: User, session, runtime: Runtime):
    await navigate(message, message.text.split()[0][1:].split("@")[0], student, session, runtime)


@router.callback_query(F.data.startswith("nav:"))
async def navigation_callback(callback: CallbackQuery, student: User, session, runtime: Runtime):
    await callback.answer()
    if isinstance(callback.message, Message):
        await navigate(callback.message, callback.data[4:], student, session, runtime)


@router.message(F.text.func(lambda value: menu_key(value) is not None))
async def menu_message(message: Message, student: User, session, runtime: Runtime):
    dest = menu_key(message.text)
    if dest == "back":
        dest = student.state_data.get("previous", "home")
    await navigate(message, dest, student, session, runtime)


@router.message(F.text, F.text.len() <= 1000)
async def goals_or_text(message: Message, student: User, session, runtime: Runtime):
    if student.state == "goals":
        student.goals = message.text.strip()
        student.state = "menu"
        await message.answer(
            tr("saved", student.language), reply_markup=inline_menu([], student.language, "profile")
        )
    elif student.state.startswith("ai"):
        from app.handlers.tutor import handle_ai_message

        await handle_ai_message(message, student, session, runtime)
    else:
        await message.answer(
            tr("welcome", student.language), reply_markup=main_menu(student.language)
        )


@router.message()
async def unsupported_message(message: Message, student: User):
    await message.answer(tr("welcome", student.language), reply_markup=main_menu(student.language))


@router.callback_query()
async def stale_callback(callback: CallbackQuery, student: User):
    await callback.answer(tr("stale", student.language), show_alert=True)
