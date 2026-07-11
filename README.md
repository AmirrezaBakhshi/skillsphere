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
for how to run the suite (15 tests total across Stage 1 + Stage 2).

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
DATABASE_URL=sqlite:///test.sqlite3 CELERY_TASK_ALWAYS_EAGER=True pytest
```

(Point `DATABASE_URL` at your real Postgres and drop `CELERY_TASK_ALWAYS_EAGER`
if you'd rather run against the full stack with a live worker.)

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
