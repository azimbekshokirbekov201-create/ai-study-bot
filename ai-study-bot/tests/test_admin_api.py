import httpx
from sqlalchemy import func, select

from app.admin.security import is_admin
from app.bot.context import Runtime
from app.main import create_app
from app.models import AdminAuditLog, BroadcastDelivery, Question, User
from app.services.subscriptions import is_premium
from scripts.seed import seed


def configured(settings):
    return settings.model_copy(
        update={
            "admin_ids": [9001],
            "admin_api_token": __import__("pydantic").SecretStr(
                "test-only-admin-key-32-characters-long"
            ),
        }
    )


HEADERS = {
    "Authorization": "Bearer test-only-admin-key-32-characters-long",
    "X-Admin-Telegram-ID": "9001",
}


def question_input(subject_id):
    return {
        "code": "admin-original",
        "subject_id": subject_id,
        "topic": "algebra",
        "difficulty": 1,
        "prompt_uz": "3 + 3 = ?",
        "prompt_en": "3 + 3 = ?",
        "correct_option": 1,
        "options": [{"text_uz": str(n), "text_en": str(n)} for n in (5, 6, 7, 8)],
        "explanation_uz": "3+3=6",
        "explanation_en": "Adding two groups of three gives six.",
    }


async def test_admin_api_auth_crud_audit_and_grants(database, settings):
    cfg = configured(settings)
    app = create_app(cfg, runtime=Runtime(cfg, database), start_bot=False)
    async with database.sessions() as session, session.begin():
        await seed(session)
        session.add(User(telegram_id=1234, display_name="Student"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/admin/dashboard")).status_code == 401
        assert (
            await client.get("/admin/dashboard", headers=HEADERS | {"X-Admin-Telegram-ID": "2"})
        ).status_code == 403
        assert (await client.get("/openapi.json")).status_code == 401
        assert (await client.get("/openapi.json", headers=HEADERS)).status_code == 200
        response = await client.get("/admin/dashboard", headers=HEADERS)
        assert response.json()["users"] == 1
        subjects = (await client.get("/admin/subjects", headers=HEADERS)).json()
        body = question_input(subjects[0]["id"])
        response = await client.post("/admin/questions", json=body, headers=HEADERS)
        assert response.status_code == 201, response.text
        question_id = response.json()["id"]
        body["prompt_en"] = "What is the sum of 3 and 3?"
        assert (
            await client.put(f"/admin/questions/{question_id}", json=body, headers=HEADERS)
        ).status_code == 200
        assert (
            await client.delete(f"/admin/questions/{question_id}", headers=HEADERS)
        ).status_code == 200
        grant = {"telegram_id": 1234, "days": 30, "reason": "Scholarship award"}
        assert (
            await client.post("/admin/subscriptions/grant", json=grant, headers=HEADERS)
        ).status_code == 201
        async with database.sessions() as session:
            user = await session.scalar(select(User).where(User.telegram_id == 1234))
            assert await is_premium(session, user.id)
        assert (
            await client.post("/admin/subscriptions/revoke", json=grant, headers=HEADERS)
        ).status_code == 200
    async with database.sessions() as session:
        assert (await session.get(Question, question_id)).active is False
        assert await session.scalar(select(func.count()).select_from(AdminAuditLog)) == 5
        assert not await is_premium(session, user.id)


async def test_admin_validation_and_broadcast_optout(database, settings):
    cfg = configured(settings)
    app = create_app(cfg, runtime=Runtime(cfg, database), start_bot=False)
    async with database.sessions() as session, session.begin():
        await seed(session)
        session.add_all(
            [
                User(telegram_id=1, display_name="Opt in"),
                User(telegram_id=2, display_name="Opt out", announcements_enabled=False),
            ]
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        invalid = question_input(999)
        invalid["correct_option"] = 4
        assert (
            await client.post("/admin/questions", json=invalid, headers=HEADERS)
        ).status_code == 422
        invalid["correct_option"] = 0
        assert (
            await client.post("/admin/questions", json=invalid, headers=HEADERS)
        ).status_code == 400
        assert (
            await client.post("/admin/broadcasts", json={"text": "Study reminder"}, headers=HEADERS)
        ).status_code == 201
        assert (
            await client.post(
                "/admin/broadcasts", content=b"x" * (1024 * 1024 + 1), headers=HEADERS
            )
        ).status_code == 413
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(BroadcastDelivery)) == 1


def test_admin_id_authorization_and_blank_secrets(settings):
    from app.config import Settings

    assert not is_admin(1, settings)
    assert is_admin(9001, configured(settings))
    cfg = Settings(_env_file=None, admin_api_token="", bot_token="", openai_api_key="")
    assert cfg.admin_api_token is None and cfg.bot_token is None and cfg.openai_api_key is None
