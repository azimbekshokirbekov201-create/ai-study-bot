# AI Study Bot

A Python 3.12 Telegram learning platform with an Uzbek (Latin) default interface,
English settings, PostgreSQL persistence, aiogram 3 and FastAPI. This repository
contains the application, migrations, original curriculum, tests and deployment
configuration. No bot token, OpenAI key or live payment credential is included.

## Implemented features

- All ten main menu entries, inline lesson navigation, Back and Main Menu controls.
- IELTS listening, reading, Writing Tasks 1/2, Speaking Parts 1/2/3, vocabulary and
  grammar. Structured writing feedback reports four criteria, mistakes, examples,
  recommendations and an **estimated, unofficial** band.
- CEFR A1–C1 lessons for all six skills, level-specific questions and performance
  recommendations. These are practice levels, not a CEFR certification service.
- SAT Math's four domains and Reading/Writing's six domains, with original
  questions and answer explanations. No official SAT items are reproduced.
- 49 original lessons and 111 original MCQs, including Premium practice items.
  This is an expandable starter curriculum, not an exhaustive exam course.
- Durable, timed quizzes, daily challenges, daily subject competitions, answer
  snapshots, progress, achievements and four leaderboard periods.
- OpenAI tutoring, grammar correction, practice generation, Premium study plans,
  persistent conversation history, daily quotas and bounded token reservations.
- Optional speech transcription and synthetic listening audio, both using OpenAI.
  Audio generation is identified to learners. Text-only speaking feedback never
  claims to assess pronunciation reliably.
- One-time Telegram Stars Premium purchases, server-side invoice matching,
  idempotent activation, expiration, refunds and audited manual grants.
- Admin Telegram commands and a protected HTTP API for questions, lessons,
  subjects, subscriptions, payments, announcements, errors and audit records.
- Durable broadcasts with recipient opt-out, bounded retry, health checks,
  structured logs, graceful shutdown, Docker, Render Blueprint and CI.

## Local installation

Use Python 3.12+, PostgreSQL 16+ and a bot created through Telegram's BotFather.
Redis is optional. On Windows use the equivalent virtualenv activation command.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
cp .env.example .env
```

Fill `BOT_TOKEN`, `POSTGRES_PASSWORD` and `DATABASE_URL`. Enter your numeric
Telegram ID in `ADMIN_IDS`. Replace the support/privacy contact placeholders.
Enable AI with your own `OPENAI_API_KEY`. Blank AI credentials disable the
integration and the bot explains this; there is no production mock provider.

Start a local database with Compose, or configure an existing PostgreSQL database:

```bash
docker compose up -d db
alembic upgrade head
python -m scripts.seed
python -m scripts.check_config
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
```

Use a URL such as
`postgresql+asyncpg://study:YOUR_URL_ENCODED_PASSWORD@localhost:5432/ai_study`.
`postgres://` and `postgresql://` URLs are normalized to asyncpg. For remote
PostgreSQL requiring TLS, use `?ssl=require`. Never disable TLS verification to
work around a certificate problem.

Local mode defaults to polling. Send `/start` in a **private** bot chat. Groups
are intentionally excluded so personal study data is not posted in group chats.
`/menu` opens the main menu and `/cancel` exits input mode. Quizzes remain in the
database; opening a new quiz abandons the previous active one.

## Docker Compose

After filling `.env`:

```bash
docker compose up --build -d
docker compose logs -f app
curl --fail http://localhost:8000/health/ready
```

Compose waits for PostgreSQL, runs migrations and insert-only seeding once, then
starts the application as a non-root user with a read-only root filesystem.
The database volume persists across application restarts. For a new release,
recreate the migration service as well as the application:

```bash
docker compose up --build --force-recreate -d migrate app
```

To add Redis, set `REDIS_URL=redis://redis:6379/0` and use
`docker compose --profile redis up --build -d`. PostgreSQL remains authoritative
for navigation and Telegram rate limits; Redis adds a shared HTTP admin limiter.
Redis is not published to the host. Use authenticated TLS Redis URLs for external
services. The bot can restart until an optional Redis instance becomes ready.

The Dockerfile accepts an optional BuildKit `proxy_ca` secret for managed build
environments. Normal Docker/Render builds do not need it. No session CA or secret
is copied into image layers.

## Configuration

Settings are validated in `app/config/settings.py`; all defaults are documented
in `.env.example`. Secret values are redacted by Pydantic and never logged.

| Variable | Meaning |
| --- | --- |
| `APP_ENV` | `development`, `test`, or `production`; production requires a bot token |
| `BOT_TOKEN` | BotFather token; blank disables the development bot |
| `DATABASE_URL` | PostgreSQL async URL; SQLite is accepted only in tests |
| `BOT_MODE` | `polling` for one local process, `webhook` for HTTPS production |
| `PUBLIC_BASE_URL` | Public HTTPS origin; falls back to `RENDER_EXTERNAL_URL` |
| `WEBHOOK_SECRET` | At least 32 characters: letters, digits, `_`, `-` |
| `WEBHOOK_PATH` | Default `/telegram/webhook` |
| `ADMIN_IDS` | Comma-separated numeric Telegram IDs, with no default administrator |
| `ADMIN_API_TOKEN` | At least 32 characters; blank disables the admin API |
| `OPENAI_API_KEY` | Required for tutoring and optional audio |
| `OPENAI_MODEL` | Default `gpt-4o-mini`; must support chat and structured outputs |
| `TTS_ENABLED`, `TTS_MODEL` | Opt-in listening audio; default `false`, `tts-1` |
| `TRANSCRIPTION_ENABLED`, `TRANSCRIPTION_MODEL` | Opt-in voice; default `false`, `gpt-4o-mini-transcribe` |
| `AI_FREE_DAILY_REQUESTS`, `AI_PREMIUM_DAILY_REQUESTS` | Defaults 3 and 30, reset at UTC midnight |
| `AI_USER_DAILY_TOKEN_BUDGET`, `AI_GLOBAL_DAILY_TOKEN_BUDGET` | Conservative token-equivalent reservation ceilings |
| `AI_MAX_INPUT_CHARS`, `AI_MAX_OUTPUT_TOKENS` | Defaults 10,000 characters and 1,100 output tokens |
| `AI_HISTORY_MESSAGES`, `AI_HISTORY_CHARS` | Defaults 10 messages and 12,000 characters of tutor history |
| `AI_TIMEOUT_SECONDS` | Default 40; provider retries are disabled |
| `AI_HISTORY_RETENTION_DAYS` | Default 30; hourly worker pruning |
| `REDIS_URL` | Optional shared HTTP rate limiter |
| `QUIZ_QUESTION_COUNT`, `QUIZ_SECONDS_PER_QUESTION` | Defaults 5 and 90; available content can yield fewer questions |
| `RATE_LIMIT_PER_MINUTE` | Default 30 Telegram updates/student; payment events are exempt |
| `PREMIUM_STARS`, `PREMIUM_DAYS` | Defaults 300 Stars and 30 days; each invoice snapshots its price/duration |
| `TERMS_VERSION` | Version recorded with each explicit purchase acceptance; update when published terms change |
| `SUPPORT_CONTACT`, `PRIVACY_CONTACT` | Publish real operator contact details before accepting students/payments |
| `PORT`, `LOG_LEVEL` | Default 8000 and INFO |

Generate webhook/admin secrets with a password manager or a secure random
generator. Do not put credentials in source, issue reports, screenshots or CI logs.

## AI behavior and costs

Tutoring history is stored in PostgreSQL and can be cleared in Settings.
Submissions go to OpenAI only after the learner opens the AI/submission flow,
which discloses that transfer. Voice is limited to two minutes and 8 MB. Raw voice
files are held in memory for transcription and are not persisted by this app.
Listening transcripts are hidden until feedback; audio requires `TTS_ENABLED`.

Each text, synthesis or transcription call reserves one request **before** the
provider call. Failed calls still consume requests. Transcribing and evaluating
one voice response uses two requests. Input UTF-8 byte counts plus the output
cap conservatively reserve text tokens; audio uses a bounded token-equivalent
allowance. Reservations are not refunded, even if actual output is shorter.
These controls bound activity, not an exact currency amount: also configure
provider account spending limits and monitor prices/model availability.

AI is given no tools, secrets, payment authority or admin data. Student text and
goals are explicitly treated as untrusted. Prompt rules reduce injection risk but
cannot guarantee model behavior. Scores and generated answers can be wrong and
should be reviewed by a qualified teacher for high-stakes decisions.

## Quiz scoring and statistics

- Every question has exactly four options at the application boundary, one
  correct option and an explanation. Admin input also validates message size.
- Quiz content, options and answer keys are snapshotted at start, so later edits
  do not change historical results or an ongoing quiz's answer key.
- Server UTC deadlines apply to the entire quiz. Challenge deadlines cannot
  cross UTC midnight. A late submission expires the attempt without a reward.
- A correct answer earns 10/15/20 points for difficulty 1/2/3. A question can
  award points only once per student per UTC day, across practice/challenges.
- Daily challenges and subject competitions have one attempt per student/day.
  All participants receive the same deterministic **Free-content** pool/order,
  irrespective of Premium status. Challenges may reuse items on later days.
- Abandoned challenge attempts cannot be restarted for another reward claim.
  Individual progress still records repeated practice answers.
- Daily/weekly/monthly/all-time rankings sum reward events. Weeks start Monday
  UTC; equal scores share a rank. Rankings are based on recorded events, not a
  mutable profile total. Public rankings show display names and points only.
- Accuracy is correct submitted answers / all submitted answers. Unanswered
  questions are not counted as submitted errors. Completed quiz count excludes
  expired/abandoned attempts. Weak-topic recommendations show sample counts;
  adaptive CEFR recommendations need at least three answers.

Free analytics show the weakest three topics; Premium shows the full topic
breakdown. First completion and a perfect completed quiz award achievements.
Writing/speaking feedback is retained as AI history; objective progress counters
and leaderboard points come from MCQ answers, not subjective AI grades.

## Premium and Telegram Stars

Digital Premium access inside Telegram is sold using **Telegram Stars (`XTR`)**,
with an empty `provider_token` and one price component. Purchases are one-time,
with no recurring renewal. A second purchase queues an additional interval.
Confirm current Telegram Stars rules and operator obligations before launch.

Buying first displays the terms and requires an explicit, single-use “I have read
and agree” button. Its preview expires after 15 minutes; acceptance version/time
are stored on the invoice. Forged or replayed confirmations cannot create invoices.
Legacy pending invoices without recorded acceptance cannot pass checkout.
This follows [Telegram's Stars requirements](https://core.telegram.org/bots/payments-stars).

Creating invoices, pressing buttons and `pre_checkout_query` approval never
grant access. Only a trusted `successful_payment` update matching the stored
payload, student, currency, amount and unique Telegram charge ID grants Premium.
Updates are trusted through authenticated Bot API polling or an HTTPS webhook
with the configured secret. There is no public API to set a payment to paid.

`/terms`, `/privacy` and `/paysupport` are implemented. Set real support/privacy
contacts and publish an operator refund policy before taking payments. Admin
refunds call Telegram's `refundStarPayment` first; verified refunds revoke the
linked interval. Refunding an earlier queued interval can leave a gap before a
later purchased interval starts. Manual scholarship grants are audited as grants
and never fabricate paid payment records.

## Administration

`/admin` checks `ADMIN_IDS` for every command/callback. Commands include:

```text
/qadd JSON
/qedit QUESTION_ID JSON
/qdelete QUESTION_ID
/grant TELEGRAM_ID DAYS REASON
/revoke TELEGRAM_ID REASON
/broadcast ANNOUNCEMENT
```

Broadcasts show a preview and require its matching confirmation button. Content
deletion deactivates records while preserving history. Full CRUD for subjects
and lessons, payment review/refunds and audit/error review are available through
the HTTP admin API. See [API examples](docs/admin-api.md).

The API and its OpenAPI schema require both
`Authorization: Bearer <ADMIN_API_TOKEN>` and an allowlisted
`X-Admin-Telegram-ID`. Keep the shared token restricted to trusted operators;
the actor header is an audit identity, not a separate cryptographic login.
All writes are audited. Error records contain a reference, type and location,
not essay text, payment payloads, credentials or raw exception messages.

Built-in Telegram navigation follows the supported exam taxonomy. Admins should
add questions/lessons under its subject codes/topics; introducing a new top-level
course also requires adding its presentation route. Seeding is insert-only and
preserves existing admin edits. Do not change seeded question codes casually:
they identify content and reward history.

## Render production deployment

Push this directory as the repository root and create a Render Blueprint using
`render.yaml`. If it is a subdirectory of another repository, set the Blueprint
path and service root directory accordingly. The template uses a paid web plan
and paid PostgreSQL, in the same region, with no public database IP allowlist.
Confirm current plan availability and pricing in your Render account.

1. Supply `BOT_TOKEN`, `ADMIN_IDS`, `OPENAI_API_KEY` and real support/privacy
   contacts when Render requests them. Generated admin/webhook secrets remain
   environment variables. You can omit OpenAI to disable AI features.
2. Render provides `RENDER_EXTERNAL_URL`; it is used as the HTTPS webhook origin.
   Set `PUBLIC_BASE_URL` explicitly if using a custom domain.
3. The release step runs `alembic upgrade head` and insert-only curriculum seed.
   Do not run schema creation through `Base.metadata.create_all` in production.
4. The image starts one Uvicorn worker on `$PORT`. Startup verifies the database,
   checks required schema access, registers commands and sets the secret webhook.
5. Readiness at `/health/ready` must return 200; liveness is `/health/live`.
   An unconfigured/failed bot is not reported ready.
6. Verify `/start`, one quiz, tutor availability, admin restrictions and support
   contacts on your actual bot. Use Telegram's documented test environment for
   purchase acceptance tests before accepting real Stars.

Production startup command (also embedded in the image):

```bash
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1 --timeout-graceful-shutdown 90 --no-access-log --no-proxy-headers
```

Polling must have one owner. Webhook replicas can coordinate through PostgreSQL
advisory locks and broadcast row locks, but migrations/seed should run once per
release. Scale the database connection allowance first (up to 20 connections per
process). Prefer a paid always-on service; free services do not promise unlimited
uptime and are inappropriate for assuming uninterrupted polling or payments.
See [operations](docs/operations.md) for failure handling, backups and retention.

## Testing and CI

```bash
python -m pytest -q
ruff check app scripts tests migrations
ruff format --check app scripts tests migrations
python -m compileall -q app scripts migrations
```

Without `TEST_DATABASE_URL`, unit/integration tests use in-memory SQLite and skip
PostgreSQL concurrency tests. To exercise the production database semantics:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost/ISOLATED_TEST_DB coverage run -m pytest -q
coverage report --include='app/*'
```

**Use a disposable test database. Test fixtures drop and recreate application
tables. Never point `TEST_DATABASE_URL` at a development database you want to
keep, or at production.** CI runs PostgreSQL 16, migration checks, the full test
suite, a coverage threshold, formatting/lint checks and an image build. All API
and Telegram mocks are confined to `tests/`. No real account is needed for CI.

Pinned dependencies and hashes are in `requirements.lock` and
`requirements-dev.lock`. To intentionally update them, use
`uv pip compile pyproject.toml --generate-hashes -o requirements.lock` and the
same command with `--extra dev -o requirements-dev.lock`, then run CI.

## Layout

```text
app/
  bot/            lifecycle context and aiogram dispatch
  handlers/       Telegram commands, menus and study flows
  keyboards/      reply/inline keyboards
  middlewares/    transactions, duplicate/rate protection, body limits
  services/       quizzes, analytics, entitlements, content and worker
  database/       sessions, metadata and locking helpers
  models/         normalized SQLAlchemy models
  repositories/   identity persistence
  ai/             OpenAI adapter, quotas and evaluation schemas
  payments/       provider interface and Telegram Stars verification
  admin/          authorization, validation, management API and audit
  localization/   shared Uzbek/English interface strings
  config/         environment validation and safe logging
migrations/       frozen Alembic migrations
scripts/          idempotent seed and configuration check
tests/            service, HTTP, dispatcher, database and concurrency tests
docs/             generated PostgreSQL schema and operator documentation
```

[Architecture](ARCHITECTURE.md) · [SQL schema](docs/schema.sql) ·
[Delivery phases](docs/phases.md) · [Validation record](docs/validation.md)
