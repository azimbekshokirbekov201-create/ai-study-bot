"""Idempotent insert-only content seeding; existing admin edits are preserved."""

import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.database import Database
from app.models import Achievement, Lesson, Question, QuestionOption, Subject
from app.services.catalog import SUBJECTS, lessons, questions


async def seed(session):
    subjects = {}
    lesson_ids = {}
    for code, (uz, en) in SUBJECTS.items():
        subject = await session.scalar(select(Subject).where(Subject.code == code))
        if subject is None:
            subject = Subject(code=code, title_uz=uz, title_en=en)
            session.add(subject)
            await session.flush()
        subjects[code] = subject.id
    for spec in lessons():
        lesson = await session.scalar(select(Lesson).where(Lesson.code == spec.code))
        if lesson is None:
            lesson = Lesson(
                code=spec.code,
                subject_id=subjects[spec.subject],
                topic=spec.topic,
                level=spec.level,
                title_uz=spec.title,
                title_en=spec.title,
                body_uz=spec.uz,
                body_en=spec.en,
                audio_script=spec.audio,
                premium_only=spec.premium,
            )
            session.add(lesson)
            await session.flush()
        lesson_ids[(spec.subject, spec.level, spec.topic)] = lesson.id
    counters = {}
    for spec in questions():
        group = (spec.subject, spec.level, spec.topic)
        counters[group] = counters.get(group, 0) + 1
        code = f"{spec.subject}-{spec.level or 'all'}-{spec.topic}-{counters[group]}"
        if await session.scalar(select(Question.id).where(Question.code == code)):
            continue
        question = Question(
            code=code,
            subject_id=subjects[spec.subject],
            lesson_id=lesson_ids[group],
            topic=spec.topic,
            level=spec.level,
            difficulty=spec.difficulty,
            prompt_uz=spec.prompt,
            prompt_en=spec.prompt,
            correct_option=spec.correct,
            explanation_uz=spec.explanation_uz,
            explanation_en=spec.explanation_en,
            premium_only=spec.premium,
        )
        session.add(question)
        await session.flush()
        session.add_all(
            [
                QuestionOption(question_id=question.id, position=i, text_uz=option, text_en=option)
                for i, option in enumerate(spec.options)
            ]
        )
    for code, uz, en in [
        ("first_quiz", "Birinchi test", "First quiz"),
        ("perfect_quiz", "Mukammal natija", "Perfect result"),
    ]:
        if not await session.scalar(select(Achievement.id).where(Achievement.code == code)):
            session.add(Achievement(code=code, title_uz=uz, title_en=en))
    await session.flush()


async def main():
    db = Database(get_settings())
    try:
        async with db.sessions() as session, session.begin():
            await seed(session)
        print("Original curriculum seeded. Existing records preserved.")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
