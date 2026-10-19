import hashlib
import random
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.base import aware, utcnow
from app.database.session import advisory_lock
from app.models import (
    Achievement,
    AttemptQuestion,
    Question,
    QuestionOption,
    QuizAnswer,
    QuizAttempt,
    RewardEvent,
    Subject,
    UserAchievement,
    UserProgress,
)
from app.services.errors import UserError
from app.services.subscriptions import is_premium


@dataclass
class AnswerResult:
    attempt: QuizAttempt
    question: AttemptQuestion | None
    correct: bool = False
    points: int = 0
    duplicate: bool = False
    expired: bool = False


class QuizService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session, self.settings = session, settings

    async def start(
        self,
        user_id: int,
        language: str,
        *,
        subject_code: str | None = None,
        topic: str | None = None,
        level: str | None = None,
        difficulty: int | None = None,
        kind: str = "practice",
        now=None,
    ):
        now = now or utcnow()
        await advisory_lock(self.session, 20, user_id)
        subject = None
        if subject_code:
            subject = await self.session.scalar(
                select(Subject).where(Subject.code == subject_code, Subject.active.is_(True))
            )
            if not subject:
                raise UserError("Fan topilmadi. / Subject unavailable.")
        challenge = None
        if kind == "daily":
            challenge = f"daily:{now.date()}"
        elif kind == "competition" and subject:
            challenge = f"competition:{subject.code}:{now.date()}"
        if challenge:
            existing = await self.session.scalar(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id, QuizAttempt.challenge_key == challenge)
                .with_for_update()
            )
            if existing:
                if existing.status == "active" and aware(existing.deadline) <= now:
                    existing.status, existing.completed_at = "expired", now
                return existing
        query = (
            select(Question)
            .join(Subject)
            .where(Question.active.is_(True), Subject.active.is_(True))
        )
        if subject:
            query = query.where(Question.subject_id == subject.id)
        if topic:
            query = query.where(Question.topic == topic)
        if level:
            query = query.where(Question.level == level)
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
        if challenge or not await is_premium(self.session, user_id, now):
            query = query.where(Question.premium_only.is_(False))
        candidates = list((await self.session.scalars(query.order_by(Question.id))).all())
        if not candidates:
            raise UserError("Savollar topilmadi. / No matching questions available.")
        if challenge:
            # Identical pool/order for every student, independent of process hash seed.
            rng = random.Random(int(hashlib.sha256(challenge.encode()).hexdigest(), 16))
            rng.shuffle(candidates)
        else:
            random.SystemRandom().shuffle(candidates)
        selected = candidates[: self.settings.quiz_question_count]
        snapshots = []
        for question in selected:
            options = (
                await self.session.scalars(
                    select(QuestionOption)
                    .where(QuestionOption.question_id == question.id)
                    .order_by(QuestionOption.position)
                )
            ).all()
            if len(options) != 4 or [o.position for o in options] != [0, 1, 2, 3]:
                raise UserError("Savol noto‘g‘ri sozlangan. / Question content is invalid.")
            snapshots.append((question, options))
        # A single active flow makes stale callbacks harmless. Old daily attempts
        # cannot be restarted after abandonment because challenge_key is unique.
        active = (
            await self.session.scalars(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id, QuizAttempt.status == "active")
                .with_for_update()
            )
        ).all()
        for previous in active:
            previous.status, previous.completed_at = "abandoned", now
        deadline = now + timedelta(seconds=self.settings.quiz_seconds_per_question * len(selected))
        if challenge:
            deadline = min(
                deadline, datetime.combine(now.date() + timedelta(days=1), time.min, UTC)
            )
        attempt = QuizAttempt(
            user_id=user_id,
            language=language,
            subject_id=subject.id if subject else None,
            question_count=len(selected),
            kind=kind,
            challenge_key=challenge,
            deadline=deadline,
            started_at=now,
        )
        self.session.add(attempt)
        await self.session.flush()
        for position, (question, options) in enumerate(snapshots):
            self.session.add(
                AttemptQuestion(
                    attempt_id=attempt.id,
                    position=position,
                    question_id=question.id,
                    subject_id=question.subject_id,
                    topic=question.topic,
                    level=question.level,
                    prompt=getattr(question, f"prompt_{language}"),
                    options=[getattr(option, f"text_{language}") for option in options],
                    explanation=getattr(question, f"explanation_{language}"),
                    correct_option=question.correct_option,
                    difficulty=question.difficulty,
                )
            )
        await self.session.flush()
        return attempt

    async def current(self, attempt: QuizAttempt):
        if attempt.status != "active":
            return None
        return await self.session.get(AttemptQuestion, (attempt.id, attempt.current_position))

    async def answer(self, user_id: int, attempt_id: UUID, position: int, option: int, now=None):
        if option not in range(4) or position < 0:
            raise UserError("Noto‘g‘ri javob. / Invalid answer.")
        await advisory_lock(self.session, 20, user_id)
        attempt = await self.session.scalar(
            select(QuizAttempt)
            .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user_id)
            .with_for_update()
        )
        if not attempt:
            raise UserError("Test topilmadi. / Quiz not found.")
        question = await self.session.get(AttemptQuestion, (attempt.id, position))
        existing = await self.session.get(QuizAnswer, (attempt.id, position))
        if existing:
            return AnswerResult(
                attempt, question, existing.correct, existing.points, duplicate=True
            )
        now = now or utcnow()
        if attempt.status == "active" and aware(attempt.deadline) <= now:
            attempt.status, attempt.completed_at = "expired", now
            return AnswerResult(attempt, question, expired=True)
        if attempt.status != "active" or position != attempt.current_position or question is None:
            raise UserError("Bu savol faol emas. / This question is no longer active.")
        correct = option == question.correct_option
        points = 0
        if correct and question.question_id:
            key = f"question:{question.question_id}:{now.date()}"
            # The per-user advisory lock also covers rewards across different attempts.
            reward = await self.session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.user_id == user_id, RewardEvent.source_key == key
                )
            )
            if reward is None:
                points = {1: 10, 2: 15, 3: 20}[question.difficulty]
                self.session.add(
                    RewardEvent(user_id=user_id, source_key=key, points=points, awarded_at=now)
                )
        self.session.add(
            QuizAnswer(
                attempt_id=attempt.id,
                position=position,
                selected_option=option,
                correct=correct,
                points=points,
                answered_at=now,
            )
        )
        attempt.correct_count += int(correct)
        attempt.points += points
        attempt.current_position += 1
        progress = await self.session.scalar(
            select(UserProgress).where(
                UserProgress.user_id == user_id,
                UserProgress.subject_id == question.subject_id,
                UserProgress.topic == question.topic,
                UserProgress.level == (question.level or ""),
            )
        )
        if progress is None:
            progress = UserProgress(
                user_id=user_id,
                subject_id=question.subject_id,
                topic=question.topic,
                level=question.level or "",
                answered=0,
                correct=0,
            )
            self.session.add(progress)
        progress.answered += 1
        progress.correct += int(correct)
        progress.updated_at = now
        if attempt.current_position == attempt.question_count:
            attempt.status, attempt.completed_at = "completed", now
            codes = ["first_quiz"]
            if attempt.correct_count == attempt.question_count:
                codes.append("perfect_quiz")
            for code in codes:
                achievement = await self.session.scalar(
                    select(Achievement).where(Achievement.code == code)
                )
                if achievement and not await self.session.get(
                    UserAchievement, (user_id, achievement.id)
                ):
                    self.session.add(
                        UserAchievement(user_id=user_id, achievement_id=achievement.id)
                    )
        await self.session.flush()
        return AnswerResult(attempt, question, correct, points)
