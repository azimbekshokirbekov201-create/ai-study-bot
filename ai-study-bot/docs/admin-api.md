# Admin API

All `/admin/*` routes and `/openapi.json` require these headers:

```text
Authorization: Bearer YOUR_ADMIN_API_TOKEN
X-Admin-Telegram-ID: YOUR_ALLOWLISTED_NUMERIC_ID
```

The shared bearer token identifies a trusted operator client. Its actor header
must be allowlisted, and writes record that actor. It is not intended for use
in untrusted browser code. There is no unauthenticated admin web dashboard.
Telegram `/admin` is the interactive operator interface; the HTTP API supports
larger editing payloads. Responses never contain bot/OpenAI keys.

| Method and route | Action |
| --- | --- |
| `GET /admin/dashboard` | User totals, UTC daily active users, quiz/answer/payment/error counts |
| `GET /admin/users?telegram_id=...` | Find registered students; paginated |
| `GET/POST /admin/questions` | List/create questions |
| `PUT/DELETE /admin/questions/{id}` | Replace/deactivate a question |
| `GET/POST /admin/subjects` | List/create subjects |
| `PUT/DELETE /admin/subjects/{id}` | Replace/deactivate a subject |
| `GET/POST /admin/lessons` | List/create lessons |
| `PUT/DELETE /admin/lessons/{id}` | Replace/deactivate a lesson |
| `GET /admin/subscriptions` | Review subscription intervals |
| `POST /admin/subscriptions/grant` | Audited manual grant |
| `POST /admin/subscriptions/revoke` | Audited revocation of all current/future intervals |
| `GET /admin/payments` | Review pending/paid/refunded invoices |
| `POST /admin/payments/{uuid}/refund` | Call Telegram refund, then revoke linked entitlement |
| `POST /admin/broadcasts` | Queue an announcement to opted-in users |
| `GET /admin/broadcasts/{uuid}/deliveries` | Review delivery outcomes |
| `GET /admin/errors` | Sanitized errors with references |
| `GET /admin/audit` | Audit history |
| `GET /openapi.json` | Full machine-readable API schema |

List endpoints accept documented `offset`/`limit` parameters; limits are capped
at 100. API bodies are capped at 1 MB, including streamed/chunked requests.
For standard validation failures the API returns 422; conflicts return 409;
domain validation errors return 400. No paid-status mutation endpoint exists.

## Create a question

Retrieve subject IDs through `GET /admin/subjects`. `options` must contain four
distinct bilingual options, in order; `correct_option` is zero-based.

```json
{
  "code": "original-linear-2026-001",
  "subject_id": 3,
  "lesson_id": null,
  "topic": "algebra",
  "level": null,
  "difficulty": 1,
  "prompt_uz": "If 3x + 4 = 19, what is x?",
  "prompt_en": "If 3x + 4 = 19, what is x?",
  "options": [
    {"text_uz": "4", "text_en": "4"},
    {"text_uz": "5", "text_en": "5"},
    {"text_uz": "6", "text_en": "6"},
    {"text_uz": "7", "text_en": "7"}
  ],
  "correct_option": 1,
  "explanation_uz": "4 ni ayiring: 3x=15. 3 ga bo‘ling: x=5.",
  "explanation_en": "Subtract 4: 3x=15. Divide by 3: x=5.",
  "active": true,
  "premium_only": false
}
```

Save it as `question.json` and use your operator environment variables:

```bash
curl --fail-with-body -X POST "$ADMIN_BASE_URL/admin/questions" \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -H "X-Admin-Telegram-ID: $ADMIN_TELEGRAM_ID" \
  -H 'Content-Type: application/json' \
  --data-binary @question.json
```

`PUT` accepts the same full object. Active attempts keep their original snapshot.
The lesson must belong to the subject. Use `A1`/`A2`/`B1`/`B2`/`C1` for CEFR
questions; use null for IELTS/SAT. Difficulty is 1, 2 or 3.

Supported subject codes are `ielts`, `cefr`, `sat_math`, `sat_rw`. Lesson topics
follow the routes in `app/handlers/navigation.py` and `app/services/catalog.py`.
Use the existing lesson code to edit the lesson shown by a menu entry.

## Manual grants and announcements

Grant/revoke body (the revoke route ignores `days`, but accepts the same shape):

```json
{"telegram_id": 123456789, "days": 30, "reason": "Scholarship approved by school"}
```

A student must have registered first. Grants append an interval and record the
reason; they do not mark a payment as paid. Announcements accept
`{"text": "Your announcement"}` and return a job UUID. API callers are trusted
operators: posting the announcement is the confirmation. Telegram commands use a
separate preview confirmation. Students can opt out in Settings at any time.
