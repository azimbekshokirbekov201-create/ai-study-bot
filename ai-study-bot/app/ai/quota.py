from uuid import UUID

from app.database.base import utcnow
from app.database.session import advisory_lock
from app.models import AIRequest, AIUsage, GlobalAIUsage
from app.services.errors import QuotaExceeded
from app.services.subscriptions import is_premium


class UsageBudget:
    """Durable reservations commit before provider calls, including failed calls.

    The token reservation is deliberately conservative (UTF-8 bytes + output cap).
    Audio uses a conservative token-equivalent allowance; hard minute/byte caps
    complement this budget. Configure provider-side spending limits as well.
    """

    def __init__(self, database, settings):
        self.database, self.settings = database, settings

    async def reserve(self, user_id: int, kind: str, tokens: int, now=None) -> UUID:
        now = now or utcnow()
        day = now.date()
        async with self.database.sessions() as session, session.begin():
            await advisory_lock(session, 4, day.toordinal())
            await advisory_lock(session, 3, user_id)
            usage = await session.get(AIUsage, (user_id, day), with_for_update=True)
            global_usage = await session.get(GlobalAIUsage, day, with_for_update=True)
            if usage is None:
                usage = AIUsage(user_id=user_id, day=day, requests=0, reserved_tokens=0)
                session.add(usage)
            if global_usage is None:
                global_usage = GlobalAIUsage(day=day, reserved_tokens=0)
                session.add(global_usage)
            premium = await is_premium(session, user_id, now)
            limit = (
                self.settings.ai_premium_daily_requests
                if premium
                else self.settings.ai_free_daily_requests
            )
            if usage.requests >= limit:
                raise QuotaExceeded(
                    "Bugungi AI so‘rovlar limiti tugadi. / Daily AI request limit reached (UTC)."
                )
            if usage.reserved_tokens + tokens > self.settings.ai_user_daily_token_budget:
                raise QuotaExceeded(
                    "Bugungi AI matn/audio budjeti tugadi. / Daily AI content budget reached (UTC)."
                )
            if global_usage.reserved_tokens + tokens > self.settings.ai_global_daily_token_budget:
                raise QuotaExceeded(
                    "AI xizmatining kunlik budjeti tugadi. / Service AI budget reached. Try tomorrow (UTC)."
                )
            usage.requests += 1
            usage.reserved_tokens += tokens
            global_usage.reserved_tokens += tokens
            reservation = AIRequest(user_id=user_id, day=day, kind=kind, reserved_tokens=tokens)
            session.add(reservation)
            await session.flush()
            return reservation.id

    async def finish(self, request_id: UUID, status: str, input_tokens=0, output_tokens=0):
        async with self.database.sessions() as session, session.begin():
            request = await session.get(AIRequest, request_id, with_for_update=True)
            if not request or request.status != "reserved":
                return
            request.status = status
            usage = await session.get(AIUsage, (request.user_id, request.day), with_for_update=True)
            usage.input_tokens += input_tokens
            usage.output_tokens += output_tokens
