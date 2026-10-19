from sqlalchemy import delete, func, select

from app.database.base import utcnow
from app.database.session import advisory_lock
from app.models import (
    AdminAuditLog,
    ApplicationError,
    Broadcast,
    BroadcastDelivery,
    Lesson,
    Payment,
    Question,
    QuestionOption,
    QuizAnswer,
    QuizAttempt,
    Subscription,
    User,
)
from app.services.errors import UserError
from app.services.subscriptions import grant_subscription


def audit(session, actor, action, target, details=None):
    session.add(
        AdminAuditLog(actor=actor, action=action, target=str(target), details=details or {})
    )


async def dashboard(session):
    midnight = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    counts = {}
    for name, model in [
        ("users", User),
        ("quizzes", QuizAttempt),
        ("answers", QuizAnswer),
        ("questions", Question),
        ("errors", ApplicationError),
    ]:
        counts[name] = await session.scalar(select(func.count()).select_from(model))
    counts["daily_active_users"] = await session.scalar(
        select(func.count()).select_from(User).where(User.last_seen_at >= midnight)
    )
    counts["completed_quizzes"] = await session.scalar(
        select(func.count()).select_from(QuizAttempt).where(QuizAttempt.status == "completed")
    )
    counts["correct_answers"] = await session.scalar(
        select(func.count()).select_from(QuizAnswer).where(QuizAnswer.correct.is_(True))
    )
    counts["paid_invoices"] = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == "paid")
    )
    return counts


async def save_question(session, data, actor, question_id=None):
    from app.models import Subject

    if not await session.get(Subject, data.subject_id):
        raise UserError("Subject not found")
    if data.lesson_id:
        lesson = await session.get(Lesson, data.lesson_id)
        if not lesson or lesson.subject_id != data.subject_id:
            raise UserError("Lesson must belong to the selected subject")
    question = (
        await session.get(Question, question_id, with_for_update=True)
        if question_id
        else Question()
    )
    if question is None:
        raise UserError("Question not found")
    duplicate = await session.scalar(select(Question.id).where(Question.code == data.code))
    if duplicate is not None and duplicate != question_id:
        raise UserError("Question code already exists")
    for key, value in data.model_dump(exclude={"options"}).items():
        setattr(question, key, value)
    session.add(question)
    await session.flush()
    await session.execute(delete(QuestionOption).where(QuestionOption.question_id == question.id))
    session.add_all(
        [
            QuestionOption(question_id=question.id, position=i, **option.model_dump())
            for i, option in enumerate(data.options)
        ]
    )
    audit(session, actor, "question.update" if question_id else "question.create", question.id)
    await session.flush()
    return question


async def grant_premium(session, telegram_id, days, actor, reason):
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        raise UserError("User must register with /start first")
    await advisory_lock(session, 5, user.id)
    result = await grant_subscription(session, user.id, days, source="admin")
    audit(session, actor, "subscription.grant", user.id, {"days": days, "reason": reason})
    return result


async def revoke_premium(session, telegram_id, actor, reason):
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        raise UserError("User not found")
    await advisory_lock(session, 5, user.id)
    rows = (
        await session.scalars(
            select(Subscription)
            .where(Subscription.user_id == user.id, Subscription.revoked_at.is_(None))
            .with_for_update()
        )
    ).all()
    for subscription in rows:
        subscription.revoked_at = utcnow()
    audit(session, actor, "subscription.revoke", user.id, {"reason": reason})


async def queue_broadcast(session, text, actor):
    broadcast = Broadcast(text=text, actor=actor)
    session.add(broadcast)
    await session.flush()
    # INSERT SELECT avoids loading every user's profile into application memory.
    from sqlalchemy import insert, literal

    await session.execute(
        insert(BroadcastDelivery).from_select(
            ["broadcast_id", "user_id", "status", "attempts"],
            select(
                literal(broadcast.id, type_=Broadcast.id.type),
                User.id,
                literal("queued"),
                literal(0),
            ).where(User.announcements_enabled.is_(True), User.blocked.is_(False)),
        )
    )
    audit(session, actor, "broadcast.queue", broadcast.id, {"characters": len(text)})
    return broadcast
