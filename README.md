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
pytest
```

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
