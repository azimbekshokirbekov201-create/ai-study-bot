"""Relational source of truth. JSON is restricted to snapshots and flexible payloads."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utcnow

JSONType = JSON().with_variant(JSONB, "postgresql")
PK = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("language IN ('uz', 'en')", name="language"),)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    username: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(2), default="uz")
    goals: Mapped[str] = mapped_column(String(1000), default="")
    cefr_level: Mapped[str] = mapped_column(String(2), default="B1")
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    state: Mapped[str] = mapped_column(String(40), default="menu")
    state_data: Mapped[dict] = mapped_column(JSONType, default=dict)
    rate_window: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    rate_count: Mapped[int] = mapped_column(Integer, default=0)
    announcements_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title_uz: Mapped[str] = mapped_column(String(160))
    title_en: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(100), unique=True)
    topic: Mapped[str] = mapped_column(String(80), index=True)
    level: Mapped[str | None] = mapped_column(String(2))
    title_uz: Mapped[str] = mapped_column(String(160))
    title_en: Mapped[str] = mapped_column(String(160))
    body_uz: Mapped[str] = mapped_column(Text)
    body_en: Mapped[str] = mapped_column(Text)
    audio_script: Mapped[str | None] = mapped_column(Text)
    premium_only: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("correct_option BETWEEN 0 AND 3", name="correct_option"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="difficulty"),
        Index("ix_question_selection", "subject_id", "topic", "level", "active"),
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"))
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"))
    topic: Mapped[str] = mapped_column(String(80))
    level: Mapped[str | None] = mapped_column(String(2))
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    prompt_uz: Mapped[str] = mapped_column(Text)
    prompt_en: Mapped[str] = mapped_column(Text)
    correct_option: Mapped[int] = mapped_column(Integer)
    explanation_uz: Mapped[str] = mapped_column(Text)
    explanation_en: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    premium_only: Mapped[bool] = mapped_column(Boolean, default=False)


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (CheckConstraint("position BETWEEN 0 AND 3", name="position"),)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    text_uz: Mapped[str] = mapped_column(String(500))
    text_en: Mapped[str] = mapped_column(String(500))


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_key"),
        CheckConstraint("status IN ('active','completed','expired','abandoned')", name="status"),
        Index("ix_attempt_user_started", "user_id", "started_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"))
    challenge_key: Mapped[str | None] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20), default="practice")
    language: Mapped[str] = mapped_column(String(2), default="uz")
    status: Mapped[str] = mapped_column(String(12), default="active")
    question_count: Mapped[int] = mapped_column(Integer)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    current_position: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttemptQuestion(Base):
    __tablename__ = "attempt_questions"
    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"))
    topic: Mapped[str] = mapped_column(String(80))
    level: Mapped[str | None] = mapped_column(String(2))
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSONType)
    explanation: Mapped[str] = mapped_column(Text)
    correct_option: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer)


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["attempt_id", "position"],
            ["attempt_questions.attempt_id", "attempt_questions.position"],
            ondelete="CASCADE",
        ),
        CheckConstraint("selected_option BETWEEN 0 AND 3", name="selected_option"),
    )
    attempt_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    selected_option: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool] = mapped_column(Boolean)
    points: Mapped[int] = mapped_column(Integer, default=0)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", "subject_id", "topic", "level"),)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    topic: Mapped[str] = mapped_column(String(80))
    level: Mapped[str] = mapped_column(String(2), default="")
    answered: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RewardEvent(Base):
    __tablename__ = "reward_events"
    __table_args__ = (
        UniqueConstraint("user_id", "source_key"),
        Index("ix_rewards_period", "awarded_at", "user_id"),
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source_key: Mapped[str] = mapped_column(String(150))
    points: Mapped[int] = mapped_column(Integer)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (Index("ix_ai_history", "user_id", "mode", "created_at"),)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(30), default="tutor")
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIUsage(Base):
    __tablename__ = "ai_usage"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, default=0)
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)


class GlobalAIUsage(Base):
    __tablename__ = "global_ai_usage"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0)


class AIRequest(Base):
    __tablename__ = "ai_requests"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(16), default="reserved")
    reserved_tokens: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount"),
        CheckConstraint("status IN ('pending','paid','refunded')", name="status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="telegram_stars")
    invoice_payload: Mapped[str] = mapped_column(String(128), unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="XTR")
    amount: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer)
    terms_version: Mapped[str | None] = mapped_column(String(40))
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12), default="pending")
    provider_charge_id: Mapped[str | None] = mapped_column(String(256), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscription_entitlement", "user_id", "ends_at", "revoked_at"),)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    payment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), unique=True
    )
    source: Mapped[str] = mapped_column(String(20), default="payment")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title_uz: Mapped[str] = mapped_column(String(160))
    title_en: Mapped[str] = mapped_column(String(160))


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class UpdateReceipt(Base):
    __tablename__ = "update_receipts"
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class ApplicationError(Base):
    __tablename__ = "application_errors"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    error_type: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(String(3500))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BroadcastDelivery(Base):
    __tablename__ = "broadcast_deliveries"
    broadcast_id: Mapped[UUID] = mapped_column(
        ForeignKey("broadcasts.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
