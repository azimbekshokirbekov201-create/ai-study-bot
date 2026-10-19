# Delivery phases

1. **Architecture:** inspected the empty workspace; established module boundaries,
   PostgreSQL transaction model and executable Python package. Compile check passed.
2. **Configuration/database:** added validated settings, normalized relational
   models, a frozen initial Alembic migration and idempotent Telegram registration.
   Registration/configuration tests passed; migration applied to PostgreSQL.
3. **Interface:** built Uzbek/English reply and inline menus, durable navigation,
   profile goals/language settings, Back/Main Menu and input cancellation.
   Menu round-trip tests passed.
4. **Quizzes:** implemented snapshots, server deadlines, automatic scoring,
   explanations, daily/subject challenges, unique rewards, achievements, topic
   progress and ranked leaderboards. Scoring/replay/deadline/ranking tests passed.
5. **Preparation modules:** added 49 lessons and 111 original MCQs across IELTS,
   CEFR A1–C1 and SAT. Added weak-topic recommendations and Premium material gates.
   Curriculum coverage and insert-only seeding tests passed.
6. **AI:** integrated the actual OpenAI SDK, structured IELTS feedback, bounded
   history, durable usage/cost reservations, error handling, Premium plans and
   optional voice/listening audio. Provider-contract, quota and failure tests passed.
7. **Payments/admin:** implemented explicit terms acceptance, fast Stars checkout,
   payment verification, renewal/expiry/refunds,
   admin authorization, CRUD, audited grants/revocation, error review and durable
   broadcasts. Payment, authorization and HTTP/dispatcher integration tests passed.
8. **Delivery:** added hashed dependency locks, Docker/Compose, Render Blueprint,
   CI, health/lifecycle checks and operator documentation. Final verification is
   recorded in `docs/validation.md`.
