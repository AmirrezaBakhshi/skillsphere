# SkillSphere

A learning & project-collaboration platform. This repo is being built
incrementally; this README covers what's implemented so far.

## Stage 1 — Authentication foundation

**Backend:** Django 4.2 + DRF, JWT auth (access token via `Authorization`
header, refresh token in an httponly cookie), Google Sign-In endpoint,
hexagonal (ports & adapters) layering for the `users` bounded context.

**Frontend:** Next.js 14 (App Router) + Tailwind, login/register/dashboard
pages, an Axios client with a silent-refresh interceptor, and a Zustand
store holding the access token in memory only.

Not yet implemented (later stages): file upload, notifications, Celery
background tasks, activity-tracking middleware, Elasticsearch search,
dashboards/analytics, real-time chat, and Nginx.

## Stage 2 — Background tasks, notifications, activity tracking, file upload

**New apps:** `projects` (file upload/download with validation + background
processing), `notifications` (in-app + email notifications), `activity`
(per-request activity logging middleware).

**Celery + Redis** now actually run background work: after registration, a
welcome email + notification are sent via a Celery task; after a project
upload, a Celery task checksums the file and flips its status from
`pending` → `processing` → `ready` (or `rejected` on failure), notifying
the owner either way.

Still not implemented (later stages): Elasticsearch search, dashboards/
analytics, real-time chat/collaboration, Nginx.

### Running Stage 2 with Docker Compose

Same as before, but there's now a `celery_worker` service — `docker compose
up --build` starts it automatically alongside everything else. No extra
steps needed.

### API reference (Stage 2 additions)

Base URL: `/api/v1/`

| Method | Path | Auth | Body / Query | Notes |
|---|---|---|---|---|
| POST | `projects/upload/` | Bearer | multipart: `title, description?, file` | 201 with the project (status `pending`); 422 if the file fails validation |
| GET | `projects/mine/` | Bearer | — | Lists only the caller's own projects |
| GET | `projects/<uuid>/download/` | Bearer | — | 404 if the project isn't yours |
| GET | `notifications/` | Bearer | `?unread=true` optional | Lists the caller's notifications |
| POST | `notifications/<id>/read/` | Bearer | — | Marks one notification read; 404 if it's not yours |
| GET | `activity/me/` | Bearer | — | The caller's own recent activity log |

File upload defaults: 25 MB max, allowed types `application/pdf`,
`application/zip`, `application/x-zip-compressed`, `image/png`,
`image/jpeg` — both configurable via `PROJECT_UPLOAD_MAX_SIZE_BYTES` /
`PROJECT_UPLOAD_ALLOWED_CONTENT_TYPES` in `backend/.env`.

Emails are printed to the console by default (`EMAIL_BACKEND` = Django's
console backend) — no real SMTP setup needed for local dev. Point
`EMAIL_BACKEND` at a real backend (e.g. SMTP or a provider's API) before
deploying anywhere real users will see it. See the **Tests** section below
for how to run the suite (34 tests total across Stage 1–5).

## Stage 3 — Dashboards, analytics, and real frontend pages

**New backend app:** `analytics` — a read-model ("reporting") layer that
aggregates data across `projects`, `notifications`, and `activity` into
two endpoints: a per-user dashboard and an admin-only system-wide
dashboard. Projects also gained a `download_count`, incremented
atomically each time a file is downloaded.

**New frontend:** the placeholder dashboard from Stage 1 is now a real
page — stat cards + a 14-day activity line chart (Recharts). Two brand
new pages: `/projects` (drag-and-drop upload, live status badges,
download) and `/notifications` (list, unread filter, mark-read). A shared
sidebar (`AppShell`) ties them together with a dark mode toggle
(persisted, respects OS preference on first load).

Still not implemented (later stages): Elasticsearch search, real-time
chat/collaboration, AI recommendations, Nginx.

### API reference (Stage 3 additions)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `dashboard/me/` | Bearer | Project counts by status, total downloads, unread notifications, 14-day activity trend |
| GET | `dashboard/admin/` | Bearer + staff | System-wide totals, signups/requests trend, top 5 most active users |

`dashboard/admin/` returns 403 for any non-staff user — make an account
staff via `/admin/` or `DJANGO_SUPERUSER_*` in `.env`.

### A note on the `analytics` app's design

Unlike `users`/`notifications`/`projects` (each of which only reads/writes
its own table), `analytics` deliberately reads across all of them in one
place. This is a common, intentional exception in hexagonal/DDD codebases
— a **CQRS-style read model** — rather than a layering mistake. See
`DOCUMENTATION_STAGE3.md` for the full reasoning.

### Known follow-up item

`npm audit` currently flags a few moderate/high severity advisories in
Next.js 14.2.35 (the latest available 14.x patch) that are only fixed by
upgrading to Next 15/16, a breaking change out of scope for this stage.
Worth revisiting before any real deployment — see `npm audit` output in
`frontend/` for specifics.

## Stage 4 — Search (Elasticsearch)

**New backend app:** `search` — indexes projects (title, description,
tags, owner) and users (username, bio) into Elasticsearch, and exposes
two public search endpoints. Projects also gained a `Tag` model
(many-to-many) so uploads can be tagged, and tags are searchable.

**Indexing is automatic and asynchronous:** a project gets indexed the
moment its background processing finishes (`status: "ready"`) — not at
upload time, so half-processed or rejected uploads never show up in
search. A user gets indexed right after registration or their first
Google sign-in. Both happen via Celery tasks (`apps/search/tasks.py`),
never inline in a request.

**New frontend:** a public `/search` page (debounced input, no login
required) searching both projects and people at once. The `/projects`
upload form gained a tags field.

Still not implemented (later stage): real-time chat/collaboration, AI
recommendations, Nginx.

### Running Stage 4 with Docker Compose

Same as before — `docker compose up --build` now also starts an
`elasticsearch` container automatically. First boot takes a little longer
while Elasticsearch initializes.

If you had projects/users created *before* adding Stage 4 (i.e. you did
Stage 1–3 first), backfill the search index once with:

```bash
docker compose exec backend python manage.py reindex_search
```

New records after that index themselves automatically — this command is
only needed for historical backfill.

### API reference (Stage 4 additions)

| Method | Path | Auth | Query | Notes |
|---|---|---|---|---|
| GET | `search/projects/?q=...` | none (public) | `q` (required) | Only returns projects with status `ready`; empty `q` returns `[]` |
| GET | `search/users/?q=...` | none (public) | `q` (required) | Matches username/bio |

Both return `503 {"detail": "Search is temporarily unavailable"}` if
Elasticsearch can't be reached, rather than a 500 — a search outage
degrades gracefully instead of looking like an application bug.

### A note on testing this stage

Elasticsearch isn't spun up as part of the automated test suite — the
`search` app's own tests (`apps/search/tests/`) verify the actual business
logic (matching, tag search, filtering out non-`ready` projects) against
an **in-memory fake** implementing the same `ProjectSearchPort`/
`UserSearchPort` interfaces the real Elasticsearch adapter implements.
This is the hexagonal architecture's testability payoff in action — see
`DOCUMENTATION_STAGE4.md` for the full explanation, including how to
manually verify the real Elasticsearch integration once you have
`docker compose` running.

## Stage 5 — Real-time chat & AI-style recommendations

**New backend apps:** `chat` (real-time 1:1 messaging over WebSockets,
via Django Channels + a Redis-backed channel layer) and `recommendations`
(a content-based project recommender using tag/description similarity).

**Chat** uses the same short-lived access token as every other endpoint —
WebSocket connections can't send a normal `Authorization` header from a
browser, so the token travels as a query param
(`ws://.../ws/chat/<id>/?token=<access_token>`) instead, validated by a
custom Channels middleware. Message history is also available over plain
REST (used to load the backlog when a chat first opens, and as a
non-WebSocket fallback).

**Recommendations** is deliberately *not* a trained ML model — it's an
explainable, testable content-based scorer (shared tags + description
word overlap) with a "popular right now" fallback for new users with no
projects yet. See `DOCUMENTATION_STAGE5.md` for why this approach was
chosen over an embeddings/LLM-based system for this stage.

**New frontend:** a `/chat` page (conversation list + a real-time thread
using a native WebSocket), a "Message" button on user search results, and
a "Recommended for you" section on the dashboard.

Still not implemented (next stage): Nginx / production deployment
hardening.

### Running Stage 5 with Docker Compose

No new services — Channels reuses Redis (already running from Stage 2)
as its channel layer backend. `docker compose up --build` picks up chat
and recommendations automatically. WebSocket support works out of the
box in dev because Django Channels replaces the `runserver` command with
an ASGI-capable one the moment `channels` is in `INSTALLED_APPS` — no
separate WebSocket server or extra command needed for local development.

### API reference (Stage 5 additions)

| Method / Protocol | Path | Auth | Notes |
|---|---|---|---|
| POST | `chat/start/` | Bearer | `{other_user_id}` — idempotent: returns the existing 1:1 conversation if one already exists |
| GET | `chat/mine/` | Bearer | Lists the caller's conversations, each with its last message |
| GET | `chat/<uuid>/messages/?before_id=` | Bearer | Message history, newest-`before_id` pagination |
| POST | `chat/<uuid>/messages/` | Bearer | REST fallback for sending a message (same validation as the WebSocket path) |
| WS | `ws/chat/<uuid>/?token=<access>` | token query param | Real-time send/receive; closes with 4001 (no/invalid token) or 4003 (not a participant) |
| GET | `recommendations/projects/` | Bearer | Up to 5 recommended projects, or popularity-based picks for a brand-new account |

### A note on testing WebSockets

The chat consumer is tested with Channels' own `WebsocketCommunicator` —
two simulated clients connect, exchange a message, and the test asserts
both sides receive it. This genuinely needs a working Redis instance
(unlike the Stage 4 search tests, which get away with an in-memory fake) —
Channels' group-broadcast mechanism *is* Redis, there's no meaningful way
to fake it. If you run these tests yourself outside Docker, make sure
Redis is reachable at whatever `REDIS_URL` your test environment uses.

## Stage 6 — Production deployment (Nginx, TLS, hardened settings)

**New:** `docker-compose.prod.yml`, `nginx/`, `backend/config/settings/prod.py`,
`backend/entrypoint.prod.sh`, `frontend/Dockerfile.prod`. This stage
doesn't add product features — it's what turns everything from Stages
1–5 into something you could actually point a real domain at.

**Nginx** sits in front of everything as the only container with ports
published to the host (80 → redirects to 443; 443 does TLS termination).
It reverse-proxies `/api/` and `/admin/` to the Django/Daphne backend,
`/ws/` to the same backend with the special headers a WebSocket upgrade
needs, `/static/` and `/media/` directly off a shared volume (bypassing
Django entirely for serving file bytes), and everything else to the
Next.js frontend.

**`config/settings/prod.py`** layers production-only settings on top of
`base.py`: `DEBUG=False`, HSTS, secure cookies, `SECURE_SSL_REDIRECT`,
WhiteNoise for static files, and — deliberately — no defaults for
`ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`, so a misconfigured production
deployment fails loudly at startup instead of silently running insecurely.

**The production server is Daphne, not Gunicorn** — Gunicorn's default
worker only speaks WSGI (plain request/response) and can't handle a
WebSocket upgrade at all. Since Stage 5 added real-time chat over
Channels, the production server has to speak ASGI end to end.

**The frontend** now has a real multi-stage production Dockerfile
(`Dockerfile.prod`) using Next.js's `output: "standalone"` build — a
minimal, self-contained server bundle, not the full dev toolchain.

### Deploying with Stage 6

```bash
cp backend/.env.prod.example backend/.env.prod
# fill in every value in backend/.env.prod - see the comments in that
# file; nothing has an insecure fallback default in production

# get a TLS cert (see nginx/certs/README.txt) and place it at:
#   nginx/certs/fullchain.pem
#   nginx/certs/privkey.pem

docker compose -f docker-compose.prod.yml --env-file backend/.env.prod up --build
```

Only ports 80 and 443 are published to the host — Postgres, Redis,
Elasticsearch, the Django backend, and the Next.js frontend are all only
reachable from other containers on the internal Docker network, not from
the outside world directly.

### Verifying the production settings are actually hardened

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py check --deploy
```

Django's own `--deploy` check flags anything still insecure (a weak
`SECRET_KEY`, `SECURE_SSL_REDIRECT` not set, etc.) — it should report
zero issues once `backend/.env.prod` is filled in properly.

### What's genuinely NOT covered by this stage

This gets you a real, working, reasonably-secured single-server
deployment — it does **not** cover horizontal scaling (multiple backend
replicas behind a load balancer), automated zero-downtime deployments,
database backups/replication, or a managed TLS renewal pipeline (Let's
Encrypt certs expire every 90 days and need a renewal job — see
`nginx/certs/README.txt`). Those are real, substantial topics of their
own, deliberately out of scope for a single stage.

## Architecture

The `users` app follows ports & adapters:

```
apps/users/
  domain/          framework-free entities, ports (interfaces), exceptions
  application/      use-case services (RegistrationService, AuthenticationService, ...)
  infrastructure/django/   Django ORM model + repository implementing the port,
                           JWT/Google adapters
  api/             DRF serializers/views/urls — thin, delegates to application services
```

Django's model auto-discovery still needs `apps/users/models.py`; it just
re-exports the real model from `infrastructure/django/models.py` so the
domain/adapter split is preserved.

## Running locally with Docker Compose

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# edit backend/.env: set a real DJANGO_SECRET_KEY and superuser password

docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Admin: http://localhost:8000/admin (uses `DJANGO_SUPERUSER_*` from `.env`)

Migrations and superuser creation run automatically on container start
(see `backend/entrypoint.sh`).

## Running the backend without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then point DATABASE_URL at a local Postgres, or sqlite:///db.sqlite3 for quick testing
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running the frontend without Docker

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Tests

```bash
cd backend
DATABASE_URL=sqlite:///test.sqlite3 CELERY_TASK_ALWAYS_EAGER=True REDIS_URL=redis://localhost:6379/0 pytest
```

(Point `DATABASE_URL` at your real Postgres and drop
`CELERY_TASK_ALWAYS_EAGER` if you'd rather run against the full stack
with a live worker. `REDIS_URL` needs to point at a real, reachable Redis
— the chat app's WebSocket tests use Django Channels' actual group
broadcast mechanism, which is backed by Redis and can't be faked the way
Stage 4's search tests fake Elasticsearch. `docker compose`'s `redis`
service works fine as the target if you're running tests from inside a
container on the same network; otherwise point it at any local Redis.)

## API reference (Stage 1)

Base URL: `/api/v1/auth/`

| Method | Path         | Auth | Body                                   | Notes |
|--------|--------------|------|-----------------------------------------|-------|
| POST   | `register/`  | none | `email, username, password`             | Returns `{ user, access }`, sets refresh cookie |
| POST   | `login/`     | none | `email, password`                       | Same response shape as register |
| POST   | `google/`    | none | `id_token`                              | `id_token` from Google Sign-In on the frontend |
| POST   | `refresh/`   | refresh cookie | — | Returns new `{ access }`, rotates the cookie |
| POST   | `logout/`    | refresh cookie | — | Blacklists the refresh token, clears the cookie |
| GET    | `me/`        | Bearer access token | — | Returns the current user |

Error responses use `{ "detail": "..." }` with the appropriate status code
(401 for bad credentials/expired tokens, 409 for a duplicate email/username).

### Test credentials

None are seeded by default. Create one via `register/`, or set
`DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_USERNAME` /
`DJANGO_SUPERUSER_PASSWORD` in `backend/.env` before first `docker compose up`
to get an admin account automatically.

## Security notes

- Access tokens are short-lived (15 min), kept in memory on the frontend only
  (never localStorage/cookies), and sent via the `Authorization` header.
- Refresh tokens (7 days) live in an httponly, `SameSite=Lax` cookie scoped to
  `/api/v1/auth/`, rotated on every use, and blacklisted on logout.
- CORS is restricted to `CORS_ALLOWED_ORIGINS`; credentials are required for
  cross-origin cookie use.
- Passwords are validated with Django's built-in validators and hashed with
  PBKDF2 by default.
