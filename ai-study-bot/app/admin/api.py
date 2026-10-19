from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.admin.schemas import BroadcastInput, GrantInput, LessonInput, QuestionInput, SubjectInput
from app.admin.security import require_admin
from app.admin.service import (
    audit,
    dashboard,
    grant_premium,
    queue_broadcast,
    revoke_premium,
    save_question,
)
from app.models import (
    AdminAuditLog,
    ApplicationError,
    BroadcastDelivery,
    Lesson,
    Payment,
    Question,
    QuestionOption,
    Subject,
    Subscription,
    User,
)
from app.payments.stars import TelegramStarsProvider
from app.services.errors import UserError

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
Actor = Annotated[str, Depends(require_admin)]


async def admin_session(request: Request):
    async with request.app.state.runtime.database.sessions() as session, session.begin():
        yield session


Session = Annotated[object, Depends(admin_session, scope="function")]


def record(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


@router.get("/dashboard")
async def get_dashboard(session: Session):
    return await dashboard(session)


@router.get("/questions")
async def list_questions(
    session: Session, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)
):
    rows = (
        await session.scalars(select(Question).order_by(Question.id).offset(offset).limit(limit))
    ).all()
    result = []
    for row in rows:
        options = (
            await session.scalars(
                select(QuestionOption)
                .where(QuestionOption.question_id == row.id)
                .order_by(QuestionOption.position)
            )
        ).all()
        result.append(record(row) | {"options": [record(option) for option in options]})
    return result


@router.post("/questions", status_code=201)
async def create_question(data: QuestionInput, session: Session, actor: Actor):
    return record(await save_question(session, data, actor))


@router.put("/questions/{question_id}")
async def edit_question(question_id: int, data: QuestionInput, session: Session, actor: Actor):
    return record(await save_question(session, data, actor, question_id))


@router.delete("/questions/{question_id}")
async def delete_question(question_id: int, session: Session, actor: Actor):
    row = await session.get(Question, question_id, with_for_update=True)
    if not row:
        raise HTTPException(404, "Not found")
    row.active = False
    audit(session, actor, "question.deactivate", row.id)
    return {"id": row.id, "active": False}


@router.get("/subjects")
async def list_subjects(session: Session):
    return [
        record(row) for row in (await session.scalars(select(Subject).order_by(Subject.id))).all()
    ]


async def save_content(session, model, data, actor, row_id=None):
    if isinstance(data, LessonInput) and not await session.get(Subject, data.subject_id):
        raise UserError("Subject not found")
    row = await session.get(model, row_id, with_for_update=True) if row_id else model()
    if row is None:
        raise HTTPException(404, "Not found")
    existing = await session.scalar(select(model.id).where(model.code == data.code))
    if existing is not None and existing != row_id:
        raise HTTPException(409, "Content code already exists")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    session.add(row)
    await session.flush()
    audit(session, actor, f"{model.__tablename__}.save", row.id)
    return record(row)


@router.post("/subjects", status_code=201)
async def create_subject(data: SubjectInput, session: Session, actor: Actor):
    return await save_content(session, Subject, data, actor)


@router.put("/subjects/{subject_id}")
async def edit_subject(subject_id: int, data: SubjectInput, session: Session, actor: Actor):
    return await save_content(session, Subject, data, actor, subject_id)


@router.get("/lessons")
async def list_lessons(
    session: Session, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    return [
        record(row)
        for row in (
            await session.scalars(select(Lesson).order_by(Lesson.id).offset(offset).limit(limit))
        ).all()
    ]


@router.post("/lessons", status_code=201)
async def create_lesson(data: LessonInput, session: Session, actor: Actor):
    return await save_content(session, Lesson, data, actor)


@router.put("/lessons/{lesson_id}")
async def edit_lesson(lesson_id: int, data: LessonInput, session: Session, actor: Actor):
    return await save_content(session, Lesson, data, actor, lesson_id)


@router.delete("/subjects/{subject_id}")
async def deactivate_subject(subject_id: int, session: Session, actor: Actor):
    row = await session.get(Subject, subject_id, with_for_update=True)
    if not row:
        raise HTTPException(404, "Not found")
    row.active = False
    audit(session, actor, "subject.deactivate", row.id)
    return {"active": False}


@router.delete("/lessons/{lesson_id}")
async def deactivate_lesson(lesson_id: int, session: Session, actor: Actor):
    row = await session.get(Lesson, lesson_id, with_for_update=True)
    if not row:
        raise HTTPException(404, "Not found")
    row.active = False
    audit(session, actor, "lesson.deactivate", row.id)
    return {"active": False}


@router.get("/users")
async def list_users(
    session: Session,
    telegram_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    query = select(User).order_by(User.id).offset(offset).limit(limit)
    if telegram_id is not None:
        query = query.where(User.telegram_id == telegram_id)
    rows = (await session.scalars(query)).all()
    return [
        {
            k: v
            for k, v in record(row).items()
            if k not in ("state", "state_data", "rate_window", "rate_count")
        }
        for row in rows
    ]


@router.get("/subscriptions")
async def list_subscriptions(
    session: Session, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    return [
        record(row)
        for row in (
            await session.scalars(
                select(Subscription).order_by(Subscription.id.desc()).offset(offset).limit(limit)
            )
        ).all()
    ]


@router.post("/subscriptions/grant", status_code=201)
async def grant(data: GrantInput, session: Session, actor: Actor):
    return record(await grant_premium(session, data.telegram_id, data.days, actor, data.reason))


@router.post("/subscriptions/revoke")
async def revoke(data: GrantInput, session: Session, actor: Actor):
    await revoke_premium(session, data.telegram_id, actor, data.reason)
    return {"revoked": True}


@router.get("/payments")
async def list_payments(
    session: Session, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    return [
        record(row)
        for row in (
            await session.scalars(
                select(Payment).order_by(Payment.created_at.desc()).offset(offset).limit(limit)
            )
        ).all()
    ]


@router.post("/payments/{payment_id}/refund")
async def refund(payment_id: UUID, request: Request, session: Session, actor: Actor):
    runtime = request.app.state.runtime
    payment = await session.get(Payment, payment_id)
    if not payment or payment.status != "paid" or not runtime.bot:
        raise HTTPException(409, "No refundable paid invoice or bot unavailable")
    user = await session.get(User, payment.user_id)
    from app.database.session import advisory_lock

    await advisory_lock(session, 5, user.id)
    await session.refresh(payment, with_for_update=True)
    if payment.status != "paid":
        raise HTTPException(409, "Invoice is no longer paid")
    # The actual Bot API must confirm the refund before local entitlement changes.
    await runtime.bot.refund_star_payment(
        user_id=user.telegram_id, telegram_payment_charge_id=payment.provider_charge_id
    )
    await TelegramStarsProvider(runtime.settings).verify_refund(
        session,
        user.id,
        payment.invoice_payload,
        payment.currency,
        payment.amount,
        payment.provider_charge_id,
    )
    audit(session, actor, "payment.refund", payment.id)
    return {"refunded": True}


@router.post("/broadcasts", status_code=201)
async def broadcast(data: BroadcastInput, session: Session, actor: Actor):
    return record(await queue_broadcast(session, data.text, actor))


@router.get("/broadcasts/{broadcast_id}/deliveries")
async def broadcast_deliveries(
    broadcast_id: UUID,
    session: Session,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    rows = (
        await session.scalars(
            select(BroadcastDelivery)
            .where(BroadcastDelivery.broadcast_id == broadcast_id)
            .order_by(BroadcastDelivery.user_id)
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [record(row) for row in rows]


@router.get("/errors")
async def list_errors(session: Session, limit: int = Query(30, ge=1, le=100)):
    return [
        record(row)
        for row in (
            await session.scalars(
                select(ApplicationError).order_by(ApplicationError.created_at.desc()).limit(limit)
            )
        ).all()
    ]


@router.get("/audit")
async def list_audit(session: Session, limit: int = Query(50, ge=1, le=100)):
    return [
        record(row)
        for row in (
            await session.scalars(
                select(AdminAuditLog).order_by(AdminAuditLog.id.desc()).limit(limit)
            )
        ).all()
    ]
