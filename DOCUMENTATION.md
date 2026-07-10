# SkillSphere — Stage 1 Documentation

This document explains **every concept, pattern, and file** used in Stage 1
(the authentication system). The README tells you how to *run* the project;
this file tells you how it *works* and *why* it's built this way — useful
for your thesis write-up, a viva/defense, or just understanding your own
codebase deeply enough to extend it.

---

## 1. The big architectural idea: Hexagonal Architecture (Ports & Adapters)

### The problem it solves

In a "normal" Django app, your business logic (e.g. "a user can't register
with an email that's already taken") tends to live directly inside Django
views or ORM models. That's fine for small apps, but it means:

- Your business rules are welded to Django. You can't unit-test them
  without spinning up the whole framework.
- If you ever swap Postgres for something else, or add a GraphQL API next
  to your REST API, you have to rewrite business logic, not just the glue
  code.

### The idea

Hexagonal architecture (also called **Ports & Adapters**, coined by Alistair
Cockburn) says: put your business logic in the **center**, completely
ignorant of frameworks, databases, or web frameworks. Everything else
(Django, Postgres, DRF, JWT libraries) is an **adapter** that plugs into
the center through a well-defined **port** (an interface).

```
        ┌─────────────────────────────────────┐
        │              adapters                │
        │   (Django ORM, DRF views, JWT lib)   │
        │   ┌───────────────────────────────┐  │
        │   │           ports               │  │
        │   │  (abstract interfaces)        │  │
        │   │   ┌───────────────────────┐   │  │
        │   │   │      domain            │   │  │
        │   │   │  (entities, rules)     │   │  │
        │   │   └───────────────────────┘   │  │
        │   └───────────────────────────────┘  │
        └─────────────────────────────────────┘
```

Data flows in through an adapter (e.g. an HTTP request hits a Django view),
gets translated into plain domain objects, passed to application-layer
"use case" services, which use **ports** (interfaces) to talk to the outside
world (like a database) without knowing *which* database it is.

### How this maps onto our code (`apps/users/`)

| Layer | Folder | What lives there | Framework-aware? |
|---|---|---|---|
| **Domain** | `domain/` | `UserEntity` (plain dataclass), `ports.py` (abstract `UserRepository`), `exceptions.py` | No — pure Python |
| **Application** | `application/` | `RegistrationService`, `AuthenticationService`, `GoogleAuthenticationService` — the actual use cases | No — pure Python |
| **Infrastructure (adapter)** | `infrastructure/django/` | `models.py` (Django ORM), `repositories.py` (implements `UserRepository` using the ORM), `authentication.py`, `google_oauth.py` | Yes — Django-specific |
| **API (adapter)** | `api/` | DRF serializers, views, urls — translates HTTP ↔ domain calls | Yes — DRF-specific |

**Why this matters practically:** `RegistrationService` (in
`application/services.py`) has *no idea* it's talking to Postgres. It just
calls `self.repository.create(...)`. In a test, you could swap in a fake
in-memory repository and test all your business rules (duplicate email
checks, etc.) without touching a database at all. This is what makes the
5 tests in `test_auth_api.py` fast (2.33 seconds for all 5).

### Domain-Driven Design (DDD) connection

Hexagonal architecture is usually paired with DDD concepts:

- **Entity**: an object with identity that persists over time —
  `UserEntity` in `domain/entities.py`. Two entities are "the same" if
  their `id` matches, even if other fields change.
- **Bounded context**: `apps/users/` is a bounded context — everything
  about "users and auth" lives together. Later stages (`apps/projects/`,
  `apps/notifications/`, etc.) will be their own bounded contexts, each
  with their own domain/application/infrastructure/api split.
- **Repository pattern**: `UserRepository` is the abstract "shape" of how
  you fetch/save users, without saying *how*. `DjangoUserRepository` is one
  implementation. This is a very common DDD pattern for decoupling business
  logic from persistence.
- **Domain exceptions**: `UserAlreadyExistsError`, `InvalidCredentialsError`
  are raised by the *domain/application* layer, not by Django. The API layer
  (`api/exception_handler.py`) then translates them into HTTP status codes
  (409, 401). This keeps "what went wrong" (a domain concept) separate from
  "how we tell the client" (an HTTP concept).

---

## 2. JWT Authentication — concepts

### Why JWT instead of Django's default session auth?

Django's built-in auth uses server-side sessions (a session ID in a cookie,
looked up in the DB/cache on every request). That's fine for a
server-rendered app, but SkillSphere's frontend is a separate Next.js app
talking to the API over HTTP — a **stateless, token-based** approach (JWT)
is the standard fit for that split, and it's explicitly requested in the
project spec ("JWT authentication").

### What a JWT actually is

A JSON Web Token is three Base64-encoded parts separated by dots:

```
<header>.<payload>.<signature>
```

- **Header**: says which algorithm signed it (e.g. HS256).
- **Payload**: claims — e.g. `user_id`, `exp` (expiry timestamp), `jti`
  (unique token ID, used for blacklisting).
- **Signature**: HMAC of the header+payload using a secret key
  (`DJANGO_SECRET_KEY`). If anyone tampers with the payload, the signature
  won't match anymore, so the server can detect forgeries **without a
  database lookup** — that's the main performance benefit over sessions.

### Access token vs. refresh token — why two tokens?

This is the central design decision in Stage 1's auth system:

| | Access token | Refresh token |
|---|---|---|
| Lifetime | 15 minutes (`SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]`) | 7 days |
| Where it's stored (frontend) | In memory (Zustand store) | httponly cookie (JS can't read it at all) |
| Sent how | `Authorization: Bearer <token>` header | Automatically, by the browser, as a cookie |
| Used for | Authenticating every API request | Getting a new access token when the old one expires |

**Why not just use one long-lived token?** If an attacker steals a token
(e.g. via XSS), a short-lived access token limits the damage window to
15 minutes. The refresh token is the "real" long-lived credential, but by
keeping it in an **httponly** cookie, client-side JavaScript (including
malicious injected JS) literally cannot read it — only the browser can
send it back to the server automatically.

**Why not put the access token in a cookie too?** Because then every
request would need CSRF protection (cookies are sent automatically by the
browser to any request, even ones a malicious site tricks your browser
into making). By keeping the access token in memory and sending it
manually via a header, cross-site requests can't "accidentally" carry your
credentials — a form of built-in CSRF resistance for the API itself. The
refresh token cookie *is* scoped (`path=/api/v1/auth/`, `SameSite=Lax`) to
minimize its exposure to exactly the one endpoint that needs it.

### Refresh token rotation & blacklisting

Every time `/auth/refresh/` is called, the old refresh token is invalidated
and a brand new one is issued (`ROTATE_REFRESH_TOKENS=True`,
`BLACKLIST_AFTER_ROTATION=True` in `SIMPLE_JWT` settings). This means a
stolen refresh token is only useful *once* — if the legitimate user refreshes
again, the attacker's copy of the old token is already blacklisted. This is
implemented using `djangorestframework-simplejwt`'s built-in
`token_blacklist` app (added to `INSTALLED_APPS`; it stores blacklisted
token IDs in the database).

### The "silent refresh" flow (frontend)

This is implemented in `frontend/lib/api.ts` via an Axios **response
interceptor**:

1. Every outgoing request gets `Authorization: Bearer <access_token>`
   attached automatically (**request interceptor**).
2. If a request comes back `401 Unauthorized` (access token expired), the
   **response interceptor** catches it, calls `/auth/refresh/` (which
   relies on the httponly cookie automatically sent by the browser), gets
   a new access token, retries the *original* failed request with the new
   token, and only then resolves the promise.
3. `refreshInFlight` is a shared promise so that if 5 requests all fail at
   once (common when a token just expired), we only call `/auth/refresh/`
   **once**, not 5 times — all 5 original requests wait on the same
   refresh call.
4. If the refresh itself fails (refresh token also expired/blacklisted),
   the user's session is cleared and they're effectively logged out.

---

## 3. Google Sign-In — how it works

This is the **ID token flow** (not the older OAuth "authorization code"
redirect flow), which is what Google's modern "Sign in with Google" button
uses:

1. On the frontend, Google's JS SDK handles the login popup and hands back
   a signed **ID token** (itself a JWT, but signed by Google, not by us).
2. The frontend sends that token to our backend (`POST /auth/google/`).
3. `apps/users/infrastructure/django/google_oauth.py` uses Google's own
   `google-auth` library to **cryptographically verify** the token is
   genuinely signed by Google and was issued for *our* app
   (`GOOGLE_OAUTH_CLIENT_ID`) — this prevents someone from forging a token
   or replaying a token meant for a different app.
4. Once verified, we extract `sub` (Google's permanent unique user ID) and
   `email`, then call `GoogleAuthenticationService.authenticate_or_register`,
   which either finds an existing account (by `google_sub`, then falls back
   to matching by `email` to link accounts) or creates a brand new one with
   an **unusable password** (`make_password(None)`) — meaning that account
   can only ever log in via Google, never via email+password, which avoids
   the security footgun of a "shadow password" nobody set.

Note: the frontend button currently exists as UI-only ("Continue with
Google") — wiring up Google's actual JS SDK to obtain the `id_token` is
straightforward but was left for you to complete with your own Google
Cloud OAuth client credentials, since that requires a real Google Cloud
project.

---

## 4. Backend file-by-file walkthrough

### `manage.py`
Django's standard CLI entrypoint. Every `python manage.py <command>` goes
through here. It just points Django at `config.settings.dev` and hands off
to Django's command machinery.

### `config/` — project-wide configuration
- **`settings/base.py`**: everything shared across environments —
  installed apps, middleware, database config (via `django-environ`,
  reading a `.env` file so secrets never get hardcoded), DRF/JWT settings,
  CORS, Celery broker config (ready for Stage 2+, unused so far).
- **`settings/dev.py`**: just flips `DEBUG=True` and relaxes `ALLOWED_HOSTS`
  — the pattern is: never branch on `if DEBUG` inside application code,
  branch by *which settings file you load* instead. A future `prod.py`
  would tighten security settings (HTTPS redirect, secure cookies, etc.).
- **`urls.py`**: the root URL router — currently just mounts the auth API
  at `/api/v1/auth/` and Django admin at `/admin/`.
- **`wsgi.py` / `asgi.py`**: the two standard entrypoints a web server uses
  to talk to Django. WSGI is synchronous (used by `gunicorn` in
  production); ASGI is async-capable and will matter once Channels
  (WebSockets for real-time notifications/chat) gets added in a later
  stage — the file already has a comment marking where that wiring goes.
- **`celery.py`**: boilerplate that creates the Celery app object and tells
  it to auto-discover `tasks.py` files in each app. Not used yet in Stage 1
  (no background tasks exist yet), but the wiring is in place so Stage 2
  can add `apps/notifications/tasks.py` etc. without touching this file.

### `apps/users/domain/` — the framework-free core
- **`entities.py`**: `UserEntity` — a `@dataclass`, not a Django model. It
  has zero imports from Django. This is deliberate: this file could be
  copy-pasted into a totally different project with a different web
  framework and still compile.
- **`ports.py`**: `UserRepository` — an `abc.ABC` (Abstract Base Class)
  declaring *what* operations the application layer needs (`create`,
  `get_by_email`, `verify_password`, etc.) without saying *how*. This is
  the "port" in "ports & adapters."
- **`exceptions.py`**: three exception classes representing things that
  can go wrong *in business terms*, not HTTP terms.

### `apps/users/application/services.py` — the use cases
Three small `@dataclass`-based service classes, each holding a
`repository: UserRepository` (the port, not a concrete class — this is
**dependency inversion**: the application layer depends on an abstraction,
and the concrete `DjangoUserRepository` is *injected* at the API layer).
Each service has one public method representing one use case:
`register()`, `authenticate()`, `authenticate_or_register()`.

### `apps/users/infrastructure/django/` — the Django adapter
- **`models.py`**: `User(AbstractUser)` — Django's ORM model. Uses a UUID
  primary key (harder to enumerate/guess than sequential integers — a
  minor security improvement, and also avoids leaking how many users have
  signed up). `USERNAME_FIELD = "email"` makes email (not username) the
  actual login identifier for Django's internal auth machinery, while
  `username` still exists as a separate, unique display handle.
- **`repositories.py`**: `DjangoUserRepository(UserRepository)` — the
  concrete adapter. Every method translates ORM objects into `UserEntity`
  objects via the `_to_entity()` helper, so nothing above this layer ever
  sees a Django model instance. `_unique_username_from()` handles the edge
  case where a Google sign-in's suggested username (derived from their
  email) collides with an existing one, by appending an incrementing
  suffix (`amir`, `amir1`, `amir2`, ...).
- **`authentication.py`**: `CookieJWTAuthentication` — currently just a
  thin subclass of `simplejwt`'s standard header-based authentication.
  It exists as an explicit extension point / naming convention so that if
  cookie-based access-token handling is ever needed, it's added here
  without touching Django settings again.
- **`google_oauth.py`**: wraps Google's official `google-auth` library to
  verify ID tokens, as explained in section 3.

### `apps/users/api/` — the DRF/HTTP adapter
- **`serializers.py`**: DRF serializers validate and shape incoming/outgoing
  data. `RegisterSerializer` reuses Django's built-in
  `validate_password()` (checks against common-password lists, minimum
  length, etc. — configured in `AUTH_PASSWORD_VALIDATORS`). `UserSerializer`
  has a `from_entity()` classmethod because it's serializing a
  `UserEntity` (a plain dataclass), not a Django model instance — DRF
  serializers can serialize *any* object with matching attributes, not
  just ORM models.
- **`views.py`**: thin `APIView` classes. Each view: (1) validates input
  via a serializer, (2) constructs the relevant application service with a
  `DjangoUserRepository()` injected, (3) calls the one use-case method,
  (4) hands the resulting `UserEntity` to `_auth_response()`, a shared
  helper that mints JWT tokens and sets the refresh cookie. Notice the
  views contain **no business logic** — no "if user already exists" checks
  live here; that's entirely in `application/services.py`.
- **`exception_handler.py`**: registered globally via
  `REST_FRAMEWORK["EXCEPTION_HANDLER"]`. DRF calls this automatically
  whenever a view raises an unhandled exception. It maps our three domain
  exceptions to HTTP statuses, then falls back to DRF's default handler
  for anything else (like DRF's own `ValidationError`).
- **`urls.py`**: maps URL paths to view classes. Nothing fancy — one path
  per endpoint.

### `apps/users/tests/test_auth_api.py`
Uses DRF's `APIClient` (a wrapper around Django's test client that
understands DRF conventions) plus `pytest-django`'s `@pytest.mark.django_db`
decorator, which gives each test a fresh, rolled-back-after test database
transaction — tests can't leak state into each other. The five tests cover:
successful registration (and that the refresh cookie gets set), duplicate
email rejection (409), wrong password rejection (401), the full
"register → use access token → call a protected endpoint" flow, and calling
refresh with no cookie present (401).

### `admin.py`
Registers `User` with Django's built-in admin site using Django's
`UserAdmin` as a base (which already knows how to handle password hashing
in the admin UI, permission checkboxes, etc.) and adds our custom fields
(`bio`, `avatar`, `google_sub`) as an extra fieldset.

### `requirements.txt`
Pinned versions of every Python dependency. Pinning (rather than `>=`)
means "this exact combination of versions is what was tested" — it avoids
the classic "works on my machine" problem when a dependency ships a
breaking change.

### `Dockerfile` (backend)
A standard Python container: installs OS-level build tools needed to
compile `psycopg2` (the Postgres driver) and Pillow-style image libraries,
installs Python dependencies, copies the code in, and runs
`entrypoint.sh` as the container's startup command.

### `entrypoint.sh`
Runs every time the backend container starts:
1. Polls Postgres until it accepts connections (containers can start in
   any order; the backend needs to wait for the database container).
2. Runs `manage.py migrate` automatically — so you never have to `exec`
   into the container manually after `docker compose up`.
3. Optionally creates a superuser from environment variables, if one with
   that email doesn't already exist (idempotent — safe to run on every
   container restart).
4. Starts the Django development server.

### `.env.example`
A template listing every environment variable the backend reads, with
placeholder/dev-safe values, so nothing sensitive is committed to git, but
anyone cloning the repo knows exactly what to configure.

---

## 5. Frontend file-by-file walkthrough

### Why Next.js "App Router"?
The `app/` directory (rather than the older `pages/` directory) is Next.js's
current recommended structure. Every folder under `app/` maps to a URL
segment, and a `page.tsx` inside it is the page rendered at that route —
e.g. `app/login/page.tsx` → `/login`.

### `app/layout.tsx`
The root layout wraps *every* page. This is where fonts are loaded once
globally: `next/font/google` downloads and self-hosts Google Fonts at
**build time** (not runtime), which avoids a runtime request to Google's
servers on every page load (better performance and privacy than a classic
`<link href="fonts.googleapis.com">` tag). The two fonts are exposed as
CSS variables (`--font-display`, `--font-body`) which Tailwind then maps to
utility classes (`font-display`, `font-body`) in `tailwind.config.js`.

### `app/globals.css`
Loads Tailwind's three layers (`base`, `components`, `utilities`) and adds
a couple of small global rules — notably `.focus-ring`, a reusable
accessible focus style (visible keyboard focus outline) applied to every
interactive element across the app.

### `tailwind.config.js`
Defines the project's **design tokens** — a named color palette (`ink`,
`paper`, `signal`, `graphite`, `line`) instead of using Tailwind's default
generic color names directly in components. This means if you ever want to
re-theme the app, you change five hex values in one file instead of
hunting through every component for `bg-gray-900` etc.

### `store/authStore.ts`
A [Zustand](https://github.com/pmndrs/zustand) store — a minimal global
state manager (much smaller and less boilerplate-y than Redux). It holds
exactly two things: the current access token and the logged-in user's
profile, both **in memory only** (explicitly never written to
`localStorage` — see the JWT section above for why).

### `lib/api.ts`
The shared Axios instance, configured with `withCredentials: true` (so the
browser includes the httponly refresh cookie on requests to the backend
domain) and the two interceptors explained in the JWT section above.

### `lib/auth.ts`
Thin wrapper functions (`registerAccount`, `login`, `logout`) — this is the
only file that needs to know the exact shape of the auth API's request/
response bodies. Pages call these functions rather than calling `api.post`
directly, which means if the API contract ever changes, only this one file
needs updating.

### `components/AuthSidePanel.tsx`
The one deliberately-designed "signature" visual element (per the
project's design approach): a mocked live activity feed, giving the
auth screens some personality tied to the actual subject matter (a
project-sharing platform) rather than a generic decorative gradient panel.
It's pure presentation — no logic, no state.

### `app/login/page.tsx` / `app/register/page.tsx`
Both are Client Components (`"use client"` — required because they use
`useState`/`useRouter`, which only work in the browser, not during
server-side rendering). Each: holds local form state, calls the relevant
`lib/auth.ts` function on submit, stores the returned session in the
Zustand store, and redirects to `/dashboard` on success. Errors from the
API (thrown by Axios as exceptions with a `.response.data.detail` — see
the backend's `exception_handler.py`) are caught and shown inline.

### `app/dashboard/page.tsx`
A placeholder protected page: on mount, if there's no `user` in the
Zustand store, it redirects to `/login`. (Note: this is a *client-side*
redirect only — a real production app would eventually want server-side
route protection too, e.g. via middleware checking a cookie-backed
session, once more pages exist worth protecting.) Includes a working
"Log out" button that calls the logout endpoint and clears local state.

### `next.config.js`, `tsconfig.json`, `.eslintrc.json`, `postcss.config.js`
Standard, largely boilerplate Next.js/TypeScript/Tailwind configuration
files — they wire the tools together (e.g. `tsconfig.json`'s `paths` entry
is what makes `@/lib/api` imports work instead of relative `../../lib/api`
paths).

### `Dockerfile` (frontend)
Installs Node dependencies and runs the Next.js dev server. (For an actual
production deployment later, this would be split into a multi-stage build
that runs `npm run build` and serves the optimized output instead of the
dev server — worth revisiting once you're closer to shipping.)

---

## 6. Docker & Docker Compose concepts

- **Dockerfile**: instructions for building one container image (one
  service). Each service (backend, frontend) has its own.
- **docker-compose.yml**: orchestrates *multiple* containers together as
  one application — defines how they're networked (services can reach each
  other by name, e.g. the backend connects to `db:5432`, not
  `localhost:5432`), what ports are exposed to your host machine, and what
  order they should start in (`depends_on` with `condition:
  service_healthy` — the backend won't even attempt to start until
  Postgres's `healthcheck` reports ready).
- **Volumes**: `postgres_data` persists your database between container
  restarts (without it, `docker compose down` would wipe your data). The
  backend/frontend also mount their source code as a volume so you can
  edit files on your host machine and see changes without rebuilding the
  image each time.

---

## 7. Security decisions recap (why, not just what)

| Decision | Why |
|---|---|
| UUID primary keys | Avoids leaking user count / sequential enumeration |
| Short-lived access token (15 min) | Limits damage if a token leaks |
| Refresh token in httponly cookie | JavaScript (incl. XSS) can't read it |
| Refresh token rotation + blacklist | A stolen refresh token is single-use |
| Access token in memory, not storage | Immune to `localStorage`-reading XSS |
| Google token verified server-side | Prevents forged/replayed identity claims |
| Django's password validators | Blocks common/short/all-numeric passwords |
| CORS restricted to known origin | Prevents arbitrary sites from calling the API with credentials |

---

## 8. Glossary (quick reference)

- **JWT** — JSON Web Token, a signed, self-contained credential.
- **Port** — an abstract interface the domain/application layer depends on.
- **Adapter** — a concrete implementation of a port using a real
  framework/library (Django ORM, DRF, a JWT library).
- **Entity** (DDD) — an object defined by identity (an `id`), not just its
  current field values.
- **Repository pattern** — an abstraction over "how data gets
  fetched/saved" so business logic doesn't depend on a specific database.
- **Dependency inversion** — high-level code (use cases) depends on
  abstractions (ports), and low-level code (Django adapters) depends on
  those same abstractions too — neither depends on the other directly.
- **Bounded context** (DDD) — a self-contained module/domain area (e.g.
  "users") with its own models and rules, deliberately decoupled from
  other contexts.
- **Silent refresh** — automatically renewing an expired access token
  behind the scenes, without interrupting the user or making them log in
  again.
- **httponly cookie** — a cookie flag that hides the cookie's value from
  JavaScript entirely; only the browser's networking layer can read/send it.
