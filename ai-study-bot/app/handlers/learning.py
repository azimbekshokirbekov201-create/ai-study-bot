from sqlalchemy import select

from app.handlers.common import send_text
from app.handlers.quizzes import show_question
from app.keyboards import choices, inline_menu
from app.localization import tr
from app.models import Lesson, Subject, UserProgress
from app.services.analytics import recommendation
from app.services.errors import UserError
from app.services.quizzes import QuizService
from app.services.subscriptions import is_premium


async def learning_navigation(message, dest, student, session, runtime):
    lang = student.language
    service = QuizService(session, runtime.settings)
    try:
        if dest == "daily":
            attempt = await service.start(student.id, lang, kind="daily")
            return await show_question(message, attempt, service, lang)
        parts = dest.split(":")
        if parts[0] == "learn":
            subject_code = parts[1]
            level = parts[2] if subject_code == "cefr" else None
            topic = parts[3] if level else parts[2]
            query = (
                select(Lesson)
                .join(Subject)
                .where(
                    Subject.code == subject_code,
                    Subject.active.is_(True),
                    Lesson.topic == topic,
                    Lesson.active.is_(True),
                )
            )
            query = (
                query.where(Lesson.level == level) if level else query.where(Lesson.level.is_(None))
            )
            lesson = await session.scalar(query.order_by(Lesson.id).limit(1))
            if not lesson:
                raise UserError("Dars topilmadi. / Lesson not available.")
            if lesson.premium_only and not await is_premium(session, student.id):
                return await message.answer(
                    tr("premium_required", lang), reply_markup=choices(["premium"], lang, "")
                )
            back = (
                f"level:{level}"
                if level
                else (
                    "sat:math"
                    if subject_code == "sat_math"
                    else "sat:rw"
                    if subject_code == "sat_rw"
                    else "ielts"
                )
            )
            text = f"{getattr(lesson, f'title_{lang}')}\n\n{getattr(lesson, f'body_{lang}')}"
            options = []
            if topic.startswith(("writing", "speaking")) or topic == "listening":
                label = (
                    ("🎧 Audioni tinglash" if lang == "uz" else "🎧 Play audio")
                    if topic == "listening"
                    else tr("submit", lang)
                )
                options.append((label, f"nav:ai:lesson:{lesson.id}"))
            else:
                options.append(
                    (
                        tr("start_quiz", lang),
                        f"nav:difficulty:{subject_code}:{level or '_'}:{topic}",
                    )
                )
                options.append((tr("competition", lang), f"nav:competition:{subject_code}"))
                progress = await session.scalar(
                    select(UserProgress).where(
                        UserProgress.user_id == student.id,
                        UserProgress.subject_id == lesson.subject_id,
                        UserProgress.topic == topic,
                        UserProgress.level == (level or ""),
                    )
                )
                rec_level, rec_diff = recommendation(progress, level or "B1")
                if level:
                    text += f"\n\n🎯 {'Tavsiya' if lang == 'uz' else 'Recommendation'}: {rec_level} · {tr(['easy', 'medium', 'hard'][rec_diff - 1], lang)}"
                    options.append((f"🎯 {rec_level}", f"nav:learn:cefr:{rec_level}:{topic}"))
            return await send_text(message, text, inline_menu(options, lang, back))
        if parts[0] == "difficulty" and len(parts) == 4:
            subject_code, level, topic = parts[1:]
            return await message.answer(
                tr("start_quiz", lang),
                reply_markup=inline_menu(
                    [
                        (tr(key, lang), f"nav:quiz:{subject_code}:{level}:{topic}:{i}")
                        for i, key in enumerate(["easy", "medium", "hard"], 1)
                    ],
                    lang,
                    f"learn:{subject_code}:{level}:{topic}"
                    if level != "_"
                    else f"learn:{subject_code}:{topic}",
                ),
            )
        if parts[0] == "quiz" and len(parts) == 5:
            subject_code, level, topic, difficulty = parts[1:]
            if int(difficulty) not in (1, 2, 3):
                raise ValueError
            attempt = await service.start(
                student.id,
                lang,
                subject_code=subject_code,
                level=None if level == "_" else level,
                topic=topic,
                difficulty=int(difficulty),
            )
            return await show_question(message, attempt, service, lang)
        if parts[0] == "competition" and len(parts) == 2:
            attempt = await service.start(
                student.id, lang, subject_code=parts[1], kind="competition"
            )
            return await show_question(message, attempt, service, lang)
    except (ValueError, IndexError):
        return await message.answer(tr("stale", lang), reply_markup=inline_menu([], lang))
    except UserError as exc:
        return await message.answer(str(exc), reply_markup=inline_menu([], lang))
    await message.answer(tr("stale", lang), reply_markup=inline_menu([], lang))
