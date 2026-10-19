from sqlalchemy import func, select

from app.models import Lesson, Question, QuestionOption, Subject
from app.services.catalog import lessons, questions
from scripts.seed import seed


def test_original_curriculum_covers_all_levels_and_sat_topics():
    specs = lessons()
    assert {s.level for s in specs if s.subject == "cefr"} == {"A1", "A2", "B1", "B2", "C1"}
    assert len([s for s in specs if s.subject == "ielts"]) == 9
    assert len([s for s in specs if s.subject == "sat_math"]) == 4
    assert len([s for s in specs if s.subject == "sat_rw"]) == 6
    for q in questions():
        assert len(q.options) == 4 and len(set(q.options)) == 4
        assert 0 <= q.correct < 4
        assert q.explanation_en and q.explanation_uz


async def test_seed_is_idempotent_and_preserves_admin_edits(session):
    await seed(session)
    first_count = await session.scalar(select(func.count()).select_from(Question))
    question = await session.scalar(select(Question).limit(1))
    question.prompt_en = "Edited by admin"
    await seed(session)
    assert await session.scalar(select(func.count()).select_from(Question)) == first_count
    assert first_count >= 100
    assert question.prompt_en == "Edited by admin"
    assert await session.scalar(select(func.count()).select_from(QuestionOption)) == first_count * 4
    assert await session.scalar(select(func.count()).select_from(Subject)) == 4
    assert await session.scalar(select(func.count()).select_from(Lesson)) == 49
