# AI Study Bot architecture

Python 3.12, aiogram 3, FastAPI and asynchronous SQLAlchemy share one process.
PostgreSQL is authoritative for identities, navigation state, content, attempts,
AI budgets, payments, entitlement and audit history. Redis is optional for the
cross-instance HTTP rate limiter. No production feature uses an in-memory database.

## Boundaries

- `app/config`: validated environment settings and redacted logging.
- `app/models`, `database`, `repositories`: normalized data and transaction helpers.
- `app/services`: quiz scoring, recommendations, ranking and subscriptions.
- `app/handlers`, `keyboards`, `localization`: Telegram presentation in Uzbek/English.
- `app/ai`: bounded OpenAI requests, durable quota reservations, tutoring/evaluation.
- `app/payments`: provider abstraction and Telegram Stars verification.
- `app/admin`: authenticated HTTP management and audited Telegram operations.
- `app/bot`: application lifecycle, update dispatch, polling/webhook ownership.

## Consistency and failure handling

Each Telegram update has a database transaction and a PostgreSQL advisory lock.
A user lock serializes ordinary updates across replicas. Pre-checkout uses a
bounded fast path without the navigation lock to meet Telegram's response window.
Eight ordinary transactions leave pool capacity for independent AI reservations.
Update receipts prevent
reprocessing committed updates. Quiz answers are also unique by attempt/position;
question snapshots protect historical results from content edits. Rewards are
unique by user/question/UTC date; daily challenges cannot be replayed for rewards.
External Telegram delivery cannot be atomically committed with PostgreSQL: a crash
after a send but before commit can repeat a message. Financial effects and quiz
rewards remain idempotent at the database layer.

AI quota is reserved and committed before an API call in a separate transaction.
Failed calls count toward the request budget to bound abuse. Provider output
tokens, input length, conversation history, timeouts and retry counts are bounded.
No tools, secrets or privileged instructions are exposed to the model.

Premium is granted only after a Telegram-signed update received through an
authenticated webhook (or authenticated Bot API polling) matches a persisted
invoice, payer, currency, amount and unique charge ID. Refunds revoke the linked
entitlement. Manual admin grants are separately audited and never forge payments.

## Deployment

Polling is local/single-instance. Production uses an HTTPS webhook secret, with
schema migration as a release step and readiness checks for PostgreSQL/Redis.
The service shuts down polling and closes SDK, HTTP and database connections.
UTC is used for all budgets, quiz deadlines, subscriptions and leaderboard periods.

## Delivery phases

1. Architecture and executable project scaffold.
2. Configuration, schema, migrations and user registration.
3. Durable navigation and bilingual menus.
4. Snapshot-based quiz engine and progress/rewards.
5. Original IELTS, CEFR A1–C1 and SAT materials.
6. OpenAI tutoring, evaluation and optional voice transcription.
7. Verified Stars payments, entitlements and audited administration.
8. Tests, deployment artifacts and operator documentation.
