# Validation record

Validated on 2026-10-19 using Python 3.12 in the managed workspace.

| Check | Result |
| --- | --- |
| Full automated suite against PostgreSQL | **42 passed**, no skips |
| Application statement coverage | **78%**, above the CI threshold of 70% |
| Concurrent AI reservations | Daily request limit cannot be exceeded |
| Concurrent quiz answers | One saved answer and one reward |
| AI reservation/user lock regression | No deadlock during a student update |
| Checkout during an in-flight student transaction | Responds without waiting for the navigation lock |
| Terms acceptance | Required, single-use, persisted; forged/replayed confirmations rejected |
| Menu dispatch | All ten menu entries, 49 lesson routes and navigation exercised |
| OpenAI SDK contract | Structured output request/response verified with test-only HTTP transport |
| Payment verification | Payer/currency/amount/payload/charge matching, replay and refund checks |
| Admin API | Authentication, editing, deactivation, audit, grants/revocation, body validation |
| Lifecycle | Polling startup/shutdown and authenticated webhook dispatch/deduplication |
| Broadcast worker | Durable delivery, late opt-out, flood waits and blocked recipient handling |
| Ruff lint and formatting | Passed |
| Python compilation/imports | Passed |
| Alembic upgrades and schema drift check | Both migrations applied; no upgrade operations detected |
| Generated PostgreSQL DDL | `docs/schema.sql` generated from the full migration chain |
| Docker image build | Passed with hash-verified dependency installation |
| Compose configuration | Passed with temporary, test-only configuration |
| Container smoke | PostgreSQL 16 migration/seed; non-root UID 10001; read-only filesystem |
| Container health without credentials | Liveness 200; readiness correctly 503 with BOT_TOKEN unset |
| Render Blueprint | Zero errors against Render's published JSON schema |

The schema contains **23 tables**. The seed provides **49 original lessons**,
**111 original MCQs** and four normalized subjects. Production data is never seeded from mocks.

Source verification commands:

```bash
ruff check app scripts tests migrations
ruff format --check app scripts tests migrations
python -m compileall -q app scripts migrations
alembic upgrade head
alembic check
coverage run -m pytest -q
coverage report --include='app/*' --fail-under=70
```

The full suite used an isolated PostgreSQL database through `TEST_DATABASE_URL`.
Without that variable, SQLite is used for routine tests and four PostgreSQL
concurrency tests are skipped. Tests drop/recreate tables in their selected DB.

Render schema source: <https://render.com/schema/render.yaml.json>.
Stars behavior reviewed against <https://core.telegram.org/bots/payments-stars>,
including explicit terms agreement, XTR invoices, pre-checkout timing,
successful-payment delivery and payment support/refunds.

No live Telegram, OpenAI or merchant credentials were supplied. Bot API and
OpenAI network responses in automated tests use clearly identified test-only
transports. Real PostgreSQL and Docker were used for database/container checks.
Live Telegram delivery, real model output quality, Stars account eligibility,
actual purchases/refunds and Render account deployment remain operator acceptance
checks after configuring credentials and contacts. No external deployment,
announcement or real payment was performed during this build.
