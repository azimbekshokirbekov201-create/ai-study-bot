# Operating AI Study Bot

## Release and recovery

Back up PostgreSQL before a schema-changing release. Run `alembic upgrade head`
once, then `python -m scripts.seed`. Seeding inserts missing records and preserves
edits. Migrations are frozen schema operations and do not import live models.
`alembic check` detects drift. `docs/schema.sql` is generated PostgreSQL DDL for
review; Alembic is the deployment source of truth.

Back up the database with your provider's managed backups and/or `pg_dump` to
encrypted access-controlled storage. Test restores to a separate database.
Keep the database private, use separate production/test accounts, and restrict
admin API network access at the platform or reverse proxy when possible.

The application has one Uvicorn worker per container. Polling needs one process
for the bot token. Never run polling alongside a production webhook owner.
Webhook mode leaves the registered webhook in place on shutdown so Telegram can
retry during a redeployment. Switching to polling deletes the webhook without
dropping pending updates. The production webhook must preserve the
`X-Telegram-Bot-Api-Secret-Token` header and use HTTPS.

Database advisory locks serialize updates across replicas. Each update receipt
commits with domain state; duplicate committed update IDs are ignored for 30 days.
Quiz answers, daily attempts, reward sources, charge IDs and payment entitlements
also have independent database uniqueness constraints. A database transaction is
held while handling an update, including bounded external calls; size the pool
and upstream concurrency accordingly (8 concurrent ordinary update transactions,
20 DB connections/process). Ordinary update slots leave capacity for independently
committed AI budgets. Polling allows up to 100 pending handler tasks.

Pre-checkout bypasses ordinary update slots and user navigation locks, has an
eight-second processing timeout and a short failure-answer deadline. This avoids
waiting for the same student's ongoing AI call within Telegram's ten-second
checkout window. Monitor upstream queueing and database pressure: rejecting a
checkout under overload is preferable to activating an unverified entitlement.

Telegram sends and PostgreSQL commits are not atomic. A process crash after a
send and before commit can repeat a message or announcement on retry. The design
does not promise exactly-once external message delivery. Reward and financial
effects remain database-idempotent. AI reservations commit independently, so a
crash can consume a request without delivering feedback. These conservative
reservations deliberately prevent uncontrolled repeat provider spending.

Webhook requests return success only after processing/commit. A slow transcription
plus evaluation may outlast Telegram's response window; Telegram may retry and the
update lock/receipt handles it. Monitor processing latency and use a lower AI
timeout or a durable incoming-job queue if traffic/latency requires early webhook
acknowledgement. Do not replace this with untracked in-process background tasks.

## Health and logs

- `/health/live`: the HTTP process responds.
- `/health/ready`: PostgreSQL and configured Redis respond and bot startup has
  succeeded; polling must still be running. It does not continuously probe
  Telegram/OpenAI external availability in webhook mode.
- Logs are structured JSON without provider request URLs, message bodies, secret
  values or raw exception messages. Application error references can be reviewed
  by admins. External log collection must follow your student-data policy.

Readiness fails if credentials are absent/invalid, schema access fails, configured
Redis is unavailable, or polling exits. Use the sanitized error type/reference to
investigate without asking students to forward secrets or full private essays.

| Symptom | Check |
| --- | --- |
| Startup DB error | DATABASE_URL, network access, TLS, release migration outcome |
| Bot disabled/not ready | BOT_TOKEN, environment settings, BotFather token status |
| Telegram conflict | Another polling owner using the same token |
| Webhook 403 | Header secret, reverse-proxy preservation, HTTPS origin |
| AI disabled | OPENAI_API_KEY and model access |
| AI unavailable | Provider status, account budget, configured timeout/model support |
| No matching questions | Active content, topic/level/difficulty and entitlement |
| Payment mismatch | Persisted invoice, payer/currency/amount and charge ID; never manually set paid |
| Broadcast not delivering | Worker health, opt-out/block state, delivery attempts, Telegram flood waits |

Broadcast workers claim one delivery row with `FOR UPDATE SKIP LOCKED`, retain the
lock during delivery, and retry transient errors up to three times. Forbidden
recipients are marked blocked. Flood waits back off without consuming an attempt.
Failed recipients are visible through the admin API; the worker never retries
them endlessly. The process runs hourly history/error/receipt maintenance.

## Data and curriculum policy

AI conversation text is retained for 30 days by default and can be cleared by
the student. Error references and AI request metadata are pruned after 90 days;
update receipts after 30. Payment, audit, quiz, usage and progress records are not
automatically deleted. Define a retention policy appropriate to your operator
and jurisdiction before launch. Fulfil export/erasure requests through the
published privacy contact; handle legally retained payment/audit records with
care rather than blindly cascading account deletion.

Usernames/display names are personal data; leaderboard names are visible to
students who open rankings. There is no session replay or full user-content
logging. Managed storage encryption, backup permissions and secret rotation are
operator responsibilities.

Original sample content should undergo teacher review before a large classroom
rollout. IELTS/CEFR estimates are not certified grades. Expand the curriculum
through the admin API; do not import copyrighted official exam banks without
appropriate rights. Run tests and content validation after changing seeded items.

## Payment operations

Stars invoices record an explicit terms version/acceptance time and are bound to
their original amount and duration, even if pricing
settings later change. Pending checkout expires after 24 hours. A genuine delayed
successful payment is still accepted if it matches a pending persisted invoice.
Charge replay never grants a second interval. Refunds must be confirmed through
Telegram before access changes; the authenticated refund service message is also
processed. Review refund failures with the charge reference, without inventing a
paid record or bypassing verification.

Publish actual support and refund terms. Test purchase/refund behavior using your
own configured bot in Telegram's documented test environment. A local mocked
payment test is a contract/regression test, not proof of account authorization or
Stars merchant eligibility.
