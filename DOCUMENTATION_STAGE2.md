# SkillSphere — Stage 2 Documentation

This picks up exactly where `DOCUMENTATION.md` (Stage 1) left off. Same
goal: explain every concept and file so you can defend/extend this code
confidently, not just run it.

Stage 2 adds three new bounded contexts — `projects`, `notifications`,
`activity` — all following the same hexagonal layering established in
Stage 1 (`domain/` → `application/` → `infrastructure/django/` → `api/`).
If a pattern was already explained in Stage 1's documentation (ports,
repositories, entities, the exception-handler mapping), it isn't repeated
in full here — only what's new or different.

---

## 1. Why three *new* apps instead of adding to `users`?

This is a direct application of **bounded contexts** (DDD): "notifications"
and "activity logs" are not really *about* users — they're their own
concerns that happen to reference a user by ID. Keeping them as separate
Django apps means:

- `apps.notifications` doesn't need to import anything from `apps.users`
  except a foreign key to `settings.AUTH_USER_MODEL` (a string reference,
  not a Python import) — so it stays decoupled.
- Each app can be tested, reasoned about, and eventually even extracted
  into its own service, independently.
- It mirrors how a real production Django codebase scales: you rarely see
  a single giant `users` app accumulating unrelated concerns.

---

## 2. Celery & Redis — the background task system

### The problem it solves

Some things a web request triggers shouldn't make the *user* wait:
sending a welcome email, or scanning/checksumming a freshly uploaded file.
If these ran synchronously inside the request/response cycle, a slow
email provider or a big file would make your API feel sluggish (or time
out). **Celery** solves this by letting you say "run this function, but
not right now, in a separate worker process" — the web request returns
immediately, and the work happens in the background.

### The moving pieces

```
 Django view                     Redis (broker)              Celery worker
 ─────────────                   ───────────────              ──────────────
 task.delay(args)  ──publish──►  a queue/list in Redis  ──consume──►  runs the function
       │                                                              │
       └── returns immediately                                       └── writes results to DB,
           (doesn't wait)                                                 sends emails, etc.
```

- **Broker** (Redis here): a message queue. Calling `.delay()` on a task
  just serializes the function name + arguments and pushes them onto a
  queue in Redis. It does *not* run the function.
- **Worker** (`celery_worker` service in `docker-compose.yml`): a separate
  long-running process (`celery -A config worker`) that watches the queue
  and actually executes tasks as they arrive, one at a time (or in
  parallel, depending on concurrency settings).
- **Result backend** (also Redis, via `CELERY_RESULT_BACKEND`): where a
  task's return value gets stored, in case you ever want to check on it
  later (`AsyncResult`). We don't currently poll results anywhere in
  Stage 2, but the wiring is there for later stages that might.

### `config/celery.py` and `config/__init__.py`

```python
app = Celery("skillsphere")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

`config_from_object(..., namespace="CELERY")` means: any Django setting
prefixed `CELERY_` becomes a Celery config option with that prefix
stripped and lowercased. E.g. `CELERY_BROKER_URL` in `settings/base.py`
becomes Celery's `broker_url`. `autodiscover_tasks()` walks every app in
`INSTALLED_APPS` looking for a `tasks.py` module and registers whatever
`@shared_task`-decorated functions it finds.

**Important bug we hit and fixed during development:** none of this
actually happens unless something *imports* `config/celery.py` — Django
doesn't do it automatically. The fix is the two lines in
`config/__init__.py`:

```python
from .celery import app as celery_app
__all__ = ("celery_app",)
```

Since `config/__init__.py` runs the moment anything imports the `config`
package (which happens immediately — `manage.py` does it on line 1), this
guarantees the Celery app exists and is configured *before* any
`@shared_task` decorator anywhere in the codebase gets a chance to bind to
a default, unconfigured Celery instance. Without this, `shared_task`s
silently fall back to Celery's default settings (which try to talk to a
local RabbitMQ broker) — exactly what happened in testing before this fix:
tasks tried connecting to `amqp://127.0.0.1:5672` instead of our Redis URL.

### `CELERY_TASK_ALWAYS_EAGER`

A setting that makes `.delay()` run the task **synchronously, immediately,
in the same process** — no Redis, no worker needed at all. This is what
Stage 2's tests use (`CELERY_TASK_ALWAYS_EAGER=True`), so `pytest` doesn't
need Redis or a worker running to verify that, say, registering a user
actually results in a welcome notification existing in the database
afterward. In real dev/production, this stays `False` so tasks genuinely
run in the background, in the separate `celery_worker` container.

### Where tasks live: `tasks.py` at the app root, not `infrastructure/`

Celery's `autodiscover_tasks()` looks for a `tasks.py` directly inside
each app's top-level package (e.g. `apps.notifications.tasks`), which is
a hardcoded convention, not something we can freely relocate without
extra configuration. So — same compromise as `apps/users/models.py` in
Stage 1 — `tasks.py` lives at the app root even though it's genuinely an
**infrastructure/adapter** concern (it imports Django, Celery, and calls
repositories directly). It's the one place in each app where that
convention wins over strict layering purity.

### The three tasks, and how they chain together

1. **`apps/users/tasks.py: send_welcome_email_task`** — triggered from
   `RegisterView` right after a successful registration. Sends a
   (console-logged, in dev) welcome email, then calls...
2. **`apps/notifications/tasks.py: create_notification_task`** — creates
   the actual `Notification` row. This is called from *three* different
   places: after registration (welcome), after a project upload starts
   (info-level "processing" notice), and after processing finishes
   (success/error). It additionally sends an email itself for `success`/
   `error` level notifications — `info`-level ones stay in-app only, so
   routine activity doesn't spam an inbox.
3. **`apps/projects/tasks.py: process_uploaded_project_task`** — triggered
   from `ProjectUploadView` right after a file is saved. Marks the project
   `"processing"`, reads the file back off disk in 1 MB chunks (so a huge
   file doesn't get loaded into memory all at once) computing a SHA-256
   checksum (a stand-in for "real" work like a virus scan or thumbnail
   generation — same pattern, different function body), then marks it
   `"ready"` and notifies the owner. Any exception marks it `"rejected"`
   and sends an error notification instead of silently losing the upload.

### Retries

Each task is decorated `@shared_task(bind=True, max_retries=3,
default_retry_delay=10)`. `bind=True` gives the function access to `self`
(the task instance), so it can call `self.retry(exc=exc)` — this
re-queues the task to run again after a delay, up to 3 times, instead of
just failing outright on a transient error (e.g. a momentary DB hiccup).

---

## 3. Notifications system

### Domain/application recap (same shape as Stage 1's users context)

- `NotificationEntity` — a plain dataclass (`id, user_id, verb, message,
  level, is_read, created_at`).
- `NotificationRepository` (port) — `create`, `list_for_user`,
  `mark_read`.
- Three tiny use-case services: `NotifyUserService`,
  `ListNotificationsService`, `MarkNotificationReadService`.
- `DjangoNotificationRepository` (adapter) — implements the port using the
  `Notification` ORM model.

### The `level` field and why it exists

`"info" | "success" | "error"` — this is what lets
`create_notification_task` decide whether to *also* send an email. It's a
deliberately simple version of what a real notification-preferences system
would eventually let users configure themselves (e.g. "email me for
errors only").

### Ownership check in `mark_read`

```python
updated = Notification.objects.filter(id=notification_id, user_id=user_id).update(is_read=True)
```

Filtering by *both* `id` and `user_id` in the same query (rather than
fetching by `id` alone and then checking ownership in Python) means a
user can never even discover whether a notification with a given ID
exists if it isn't theirs — the query simply returns zero rows either way,
and the view returns a 404 in both cases (doesn't distinguish "wrong
owner" from "doesn't exist" in its response, which is the safer behavior
here since we can't easily justify letting users know that a notification
ID exists at all if it isn't theirs).

---

## 4. Activity tracking middleware

### Why middleware, and not a view decorator or signal?

Django **middleware** wraps *every* request/response, regardless of which
view handled it — that's exactly the fit for "log every API hit," since
it lets us capture the action in one place instead of adding logging code
to every single view function across every app.

### How it's wired: `MIDDLEWARE` ordering matters

```python
MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.activity.infrastructure.django.middleware.ActivityLoggingMiddleware",
]
```

Django's middleware list is processed top-to-bottom on the way *in*
(request) and bottom-to-top on the way *out* (response). Being last in
the list means `ActivityLoggingMiddleware.__call__` is the **outermost**
wrapper around the actual view call — it calls
`response = self.get_response(request)` (which runs the entire rest of
the stack, including the DRF view itself), and only *after* that returns
does it log anything. That's what lets it read the final `response.status_code`
and the authenticated `request.user` (see next section for why that works).

### The `request.user` subtlety with DRF + JWT

This one is worth understanding precisely, because it's easy to get
wrong: Django's own `AuthenticationMiddleware` only knows about
**session-based** auth — it doesn't know anything about our JWT scheme.
So how does the middleware see the right `request.user` for a JWT-
authenticated API call?

DRF wraps Django's `HttpRequest` in its own `Request` object inside
`APIView.dispatch()`. When a view (or DRF internals) accesses
`request.user` for the first time, DRF's `Request.user` **property**
lazily authenticates (calling `CookieJWTAuthentication` under the hood)
and then does this:

```python
self._user = user
self._request.user = user   # <- writes back onto the underlying Django HttpRequest
```

That `self._request` is the *same* object our middleware is holding a
reference to (Django passes one `HttpRequest` through the whole
middleware chain and into the view). So by the time `get_response()`
returns control back to our middleware, `request.user` — read on the
plain Django object — already reflects whichever user DRF authenticated,
even though `AuthenticationMiddleware` itself never touched JWTs. If a
request was never authenticated (a public endpoint, or a failed auth
attempt), `request.user` stays Django's `AnonymousUser`, and we record
`user_id=None`.

### Fail-safe logging

```python
try:
    self.service.record(...)
except Exception:
    pass
```

Deliberate: activity logging is a nice-to-have for analytics, not a
correctness requirement. A bug or DB hiccup in the logging path must never
turn into a 500 error for an otherwise-successful API request — so any
exception here is swallowed rather than propagated.

### Ignored paths

`/admin/`, `/static/`, `/media/` are skipped — logging every static asset
request would be noise, not signal, for "what are users doing" analytics.

---

## 5. File upload & download (`projects` app)

### Validation lives in the application layer, not the view

```python
class UploadProjectService:
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
    allowed_content_types: tuple[str, ...] = ...

    def upload(self, ...):
        if file_size > self.max_file_size_bytes:
            raise InvalidFileError(...)
        if content_type not in self.allowed_content_types:
            raise InvalidFileError(...)
        return self.repository.create(...)
```

The limits are **constructor parameters with defaults**, not hardcoded
constants buried in the method — the view passes in the actual values from
Django settings (`settings.PROJECT_UPLOAD_MAX_SIZE_BYTES`, etc.). This
means: (a) the service itself has zero Django imports, so it's trivially
unit-testable with any limits you like, and (b) a test can override
`settings.PROJECT_UPLOAD_MAX_SIZE_BYTES` to something tiny to deliberately
trigger the "file too big" path, exactly as `test_upload_rejects_oversized_file`
does.

**Honest limitation, worth knowing:** `content_type` here comes from the
`Content-Type` header the *browser* sends with the upload — it's whatever
the client claims the file is, not something we've verified by inspecting
the file's actual bytes (its "magic numbers"). A malicious client could
lie about this. A hardened version would sniff the real file signature
(e.g. via `python-magic` or checking magic bytes manually) rather than
trusting the declared content type. This wasn't added in Stage 2 to avoid
a new system dependency (`python-magic` needs `libmagic` installed at the
OS level) — worth adding before this goes anywhere near production traffic
with untrusted uploads.

### Where uploaded files actually live: `project_upload_path`

```python
def project_upload_path(instance, filename):
    return f"projects/{instance.owner_id}/{instance.id}/{filename}"
```

Namespacing by both `owner_id` and the project's own `id` means: (a) two
users can never collide/overwrite each other's files even if they upload
identically-named files, and (b) listing "everything user X has ever
uploaded" is a simple filesystem operation if you ever needed it outside
Django. This works even though `save()` hasn't been called yet, because
`id = models.UUIDField(default=uuid.uuid4, ...)` generates the UUID the
moment the Python object is *instantiated* in memory, not when it's saved.

### Downloading: streaming instead of loading into memory

```python
return FileResponse(open(file_path, "rb"), as_attachment=True)
```

`FileResponse` streams the file back to the client in chunks rather than
reading the whole thing into memory first — important once files start
approaching the 25 MB upload limit (or whatever you configure it to).

### Ownership check on download

`GetProjectForDownloadService.get_file_path` calls
`repository.get_for_owner(project_id=..., owner_id=...)` first — if that
returns `None` (either the project doesn't exist, *or* it belongs to
someone else), it raises `ProjectNotFoundError`, mapped to a 404. Same
principle as the notifications "mark read" endpoint: we don't leak
whether a given ID exists to someone who doesn't own it.

### Status lifecycle

```
pending  →  processing  →  ready
                        ↘  rejected   (on any processing failure)
```

The API response from the upload endpoint reflects the project's status
**at creation time** (`"pending"`) — even though, in tests with eager
Celery, the background task has usually already finished by the time the
HTTP response is being built. This is intentional and matches how the
system behaves for real, with an actual asynchronous worker: the client
gets an immediate "upload accepted, processing has started" response and
finds out the final status either by polling `GET /projects/mine/` or by
picking up the notification that gets created once processing completes.

---

## 6. New settings introduced in Stage 2

| Setting | Purpose |
|---|---|
| `CELERY_TASK_ALWAYS_EAGER` | Run tasks synchronously in-process (tests, or debugging without a worker) |
| `EMAIL_BACKEND` | Where outgoing emails go — console (dev) vs. real SMTP/API (prod) |
| `DEFAULT_FROM_EMAIL` | The "From" address on outgoing emails |
| `PROJECT_UPLOAD_MAX_SIZE_BYTES` | Upload size ceiling, enforced in `UploadProjectService` |
| `PROJECT_UPLOAD_ALLOWED_CONTENT_TYPES` | Whitelisted MIME types for uploads |

---

## 7. Testing patterns worth noticing

- **`apps/conftest.py`**: a shared `authed_client` fixture — registers a
  fresh user via the real API (not a shortcut/factory), grabs the access
  token from the response, and pre-configures an `APIClient` with the
  `Authorization` header set. Every Stage 2 test that needs "a logged-in
  user" reuses this one fixture instead of repeating the register/login
  dance.
- **`SimpleUploadedFile`**: Django's test helper for simulating an
  uploaded file in-memory, with a given name/content/content-type, without
  needing a real file on disk or a real HTTP multipart request.
- **`settings` fixture** (`pytest-django`): lets a single test override one
  Django setting (e.g. `settings.PROJECT_UPLOAD_MAX_SIZE_BYTES = 10`) for
  just that test, automatically reverted afterward — used in
  `test_upload_rejects_oversized_file` to trigger the size-limit path
  without needing a genuinely 25MB+ test fixture file.
- Running the whole suite needs `CELERY_TASK_ALWAYS_EAGER=True` in the
  environment (not just as a per-test settings override) — Celery builds
  and caches its configuration once per process the first time it's
  needed, so a later per-test settings override doesn't retroactively
  change how `.delay()` behaves. This is a genuine Celery/pytest gotcha,
  not a workaround for a bug in our code — worth remembering if you add
  more Celery-dependent tests later.

---

## 8. Glossary additions (Stage 2 terms)

- **Broker** — the message queue (Redis, here) that holds pending task
  invocations between "someone called `.delay()`" and "a worker actually
  ran it."
- **Worker** — the separate process that consumes tasks off the broker
  and executes them.
- **Eager mode** — running a Celery task synchronously in the calling
  process, skipping the broker/worker entirely (used for tests).
- **Idempotent** — safe to run more than once without causing harm (e.g.
  `entrypoint.sh`'s superuser creation checks "does this email already
  exist" first).
- **Bounded context** — see Stage 1's documentation; `projects`,
  `notifications`, and `activity` are each their own bounded context here.
