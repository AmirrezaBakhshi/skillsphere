# SkillSphere — Stage 6 Documentation

Continues from `DOCUMENTATION.md` through `DOCUMENTATION_STAGE5.md`. This
stage adds no new product features — it's the "make it safe to actually
deploy" stage, which is its own distinct skill from building features in
the first place. Every concept here is genuinely new relative to Stages
1–5, since this is the first time the project has dealt with anything
outside Django/Next.js itself.

---

## 1. Why a reverse proxy at all

### What changes about the network topology

In every previous stage's `docker-compose.yml`, the backend (port 8000)
and frontend (port 3000) each published their port directly to your
laptop — `localhost:8000` and `localhost:3000` both worked because Docker
mapped those container ports straight through.

In `docker-compose.prod.yml`, **only Nginx** publishes ports (80 and 443).
Every other service — Postgres, Redis, Elasticsearch, the Django backend,
the Next.js frontend — has no `ports:` entry at all, meaning they're only
reachable from *other containers on the same Docker network*, never
directly from outside. A visitor's browser only ever talks to Nginx;
Nginx alone decides which internal service handles the request.

### Why this is more than just convenience

- **One thing to secure at the network edge.** Postgres, Redis, and
  Elasticsearch have no business being reachable from the public
  internet at all — Stage 4's Elasticsearch, for instance, runs with
  `xpack.security.enabled: "false"` (no password), which is only an
  acceptable tradeoff *because* it's now unreachable from outside Docker's
  internal network in production. If Elasticsearch's port were still
  published to the host the way it is in dev, that setting alone would be
  a serious exposure.
- **One place to terminate TLS.** Rather than teaching Django and Next.js
  each how to speak HTTPS individually, Nginx handles the TLS
  handshake/certificate once, then talks plain HTTP to the backend and
  frontend over the *internal* Docker network (which never leaves the
  host machine, so it doesn't need its own encryption).
- **One place to route by path.** A single domain (say,
  `skillsphere.example.com`) needs to serve the Next.js app at `/`, the
  Django API at `/api/`, the admin at `/admin/`, and WebSocket
  connections at `/ws/` — Nginx's `location` blocks are what makes one
  domain able to transparently serve two completely different
  applications (Django and Next.js) depending on the URL path.

### Reading `nginx/conf.d/skillsphere.conf`'s structure

```nginx
upstream backend {
    server backend:8000;
}
upstream frontend {
    server frontend:3000;
}
```

An `upstream` block is just a named alias for "wherever this actually
lives" — `backend` here resolves to the `backend` container's hostname
on the Docker network (Docker's built-in DNS resolves service names from
`docker-compose.yml` automatically; this is the same mechanism that let
`DATABASE_URL=postgres://...@db:5432/...` work since Stage 1).

```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

The first `server` block's only job is redirecting any plain HTTP
request to HTTPS — a permanent redirect (`301`) so browsers and search
engines remember to use HTTPS next time without being told again.

```nginx
location /api/ {
    proxy_pass http://backend;
    include /etc/nginx/proxy_params.conf;
}
```

`proxy_pass` forwards the request to the named upstream. `proxy_params.conf`
(a small shared file, included in multiple `location` blocks to avoid
repeating the same five lines four times) sets headers like
`X-Forwarded-For` and `X-Forwarded-Proto` — these tell Django what the
*original* request actually looked like (real client IP, whether it was
HTTPS) even though, from Django's point of view, every request is now
arriving as plain HTTP from Nginx's own internal IP.

---

## 2. WebSocket proxying: why chat needs its own `location` block

A WebSocket connection starts life as a completely normal-looking HTTP
request — but with two special headers (`Upgrade: websocket` and
`Connection: Upgrade`) asking the server to switch protocols mid-request.
By default, Nginx doesn't forward those headers to whatever it's proxying
to — a proxied request/response cycle is exactly what Nginx expects, not
a promise to keep a connection open indefinitely.

```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

- `proxy_http_version 1.1` — WebSocket upgrades require HTTP/1.1 (Nginx
  defaults to 1.0 for proxied requests otherwise, which doesn't support
  the upgrade mechanism at all).
- `proxy_set_header Upgrade $http_upgrade;` /
  `proxy_set_header Connection "upgrade";` — these two lines are what
  actually forward the client's upgrade request through to Daphne, rather
  than Nginx handling it as an ordinary request and Daphne never finding
  out the client wanted a WebSocket at all.
- `proxy_read_timeout 3600s;` — Nginx normally closes a proxied connection
  if it's idle for a while (the default is quite short, meant for normal
  request/response traffic). A chat conversation might sit open with no
  new messages for a long time without meaning the connection is dead —
  this extends the timeout to an hour so Nginx doesn't kill a perfectly
  healthy, just-quiet chat connection.

This is a direct, concrete payoff of Stage 5's `/ws/` URL prefix
(`apps/chat/infrastructure/channels/routing.py`) being a distinct path
from `/api/` — Nginx can tell the two kinds of traffic apart purely by
URL and route each through the settings it actually needs.

---

## 3. TLS / HTTPS termination

### What "termination" means here

Nginx holds the actual TLS certificate and private key
(`nginx/certs/fullchain.pem` / `privkey.pem`) and is the only place in
the whole system that ever speaks HTTPS to the outside world. Once a
request's TLS layer is decrypted by Nginx, everything *behind* Nginx
(the trip to `backend:8000` or `frontend:3000`) happens as plain HTTP
over the internal Docker network — this is "TLS termination": the
encrypted connection *ends* (terminates) at Nginx.

### Why Django still needs to know the original request was HTTPS

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

Since Django only ever sees plain HTTP from Nginx, by default it would
have no way to know the original visitor connected over HTTPS — which
matters because several of Django's own security features (redirecting
insecure requests, marking cookies as HTTPS-only) need to know that. The
convention across virtually every reverse-proxy setup is: the proxy adds
an `X-Forwarded-Proto: https` header saying "trust me, this really did
arrive over HTTPS even though I'm handing it to you as plain HTTP" — and
Django is told, via this one setting, to actually trust and read that
header. This must **only** ever be enabled when you're certain something
like Nginx is truly in front of Django doing real TLS termination —
trusting this header from an untrusted source would let anyone spoof
"this was HTTPS" by just setting the header themselves.

### The other production-only security settings, briefly

| Setting | What it does |
|---|---|
| `SECURE_SSL_REDIRECT` | Django-level HTTPS redirect (belt-and-suspenders alongside Nginx's own 80→443 redirect) |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | Cookies only ever sent over HTTPS, never accidentally over plain HTTP |
| `SECURE_HSTS_SECONDS` (+ subdomains/preload) | Tells browsers "remember to always use HTTPS for this domain, for this many seconds, without even trying HTTP first" |
| `SECURE_CONTENT_TYPE_NOSNIFF` | Stops browsers from guessing a file's type differently than the server declared (a minor but real category of exploit) |
| `X_FRAME_OPTIONS = "DENY"` | Stops the whole site from being embedded in an `<iframe>` on someone else's page (clickjacking protection) |

None of these are enabled in `dev.py` — they're specifically
production-only, because several of them (HSTS in particular) actively
break plain-HTTP local development if left on.

### Why `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` have *no default* in `prod.py`

```python
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
```

Every other environment variable read via `django-environ` throughout
this project uses `env(..., default=...)` — a sensible fallback if the
variable is missing. These two, deliberately, do not. If
`DJANGO_ALLOWED_HOSTS` isn't set in `backend/.env.prod`, Django simply
refuses to start at all, with a clear error, rather than silently falling
back to something that would work but be insecure (like accepting `*`,
which dev's `ALLOWED_HOSTS = ["*"]` does on purpose, since blocking
arbitrary `Host` headers only matters once you're actually exposed to the
internet).

---

## 4. Serving static and media files without Django in the loop

### The problem

Every request Django personally handles costs more (Python interpreter,
ORM, middleware chain) than a web server just reading bytes off disk and
sending them back. Static files (Django admin's CSS/JS, DRF's browsable
API assets) and media files (Stage 2's user-uploaded project files) never
need any of that — they're just files.

### Two different strategies, for two different reasons

**Static files → WhiteNoise** (`whitenoise.middleware.WhiteNoiseMiddleware`,
`STATICFILES_STORAGE`): these files are baked into the backend Docker
image at build time (`collectstatic` runs during `entrypoint.prod.sh`,
copying every app's static assets into one `STATIC_ROOT` folder). Since
they live inside the backend container itself, WhiteNoise serves them
efficiently straight out of Django/Daphne's own process — simple, and
genuinely fine at this scale (WhiteNoise's `CompressedManifestStaticFilesStorage`
also gzips them and adds cache-busting hashes to filenames automatically).

**Media files → a shared volume + Nginx `alias`**: unlike static files,
media files are created *at runtime* (someone uploads a project at 3am,
long after the containers already started) — they can't be baked into an
image. Instead, `docker-compose.prod.yml` mounts a named volume
(`media_files`) into *both* the backend container (where Django writes
newly uploaded files) and the Nginx container (read-only, where Nginx
serves them directly):

```nginx
location /media/ {
    alias /app/media/;
}
```

This is why the volume is shared between exactly those two containers
rather than baked into an image — Nginx reads the same files off disk
that Django just wrote, without ever proxying the request through Django
at all for the actual byte-serving part.

---

## 5. Daphne vs. Gunicorn: why the production server had to change

### What changed, and why now specifically

`requirements.txt` originally included `gunicorn` from Stage 1 onward, as
a generically-reasonable "you'll want a real production server
eventually" placeholder — reasonable at the time, since Stage 1 was pure
HTTP request/response. Stage 5 changed that: Gunicorn's default worker
model only understands **WSGI** (the plain, one-request-in
one-response-out interface Django has always exposed) — it has no concept
of a connection that stays open for a two-way, ongoing conversation, like
a WebSocket. Once real-time chat existed, a production server that can
only speak WSGI would simply be unable to serve `/ws/` connections at all.

**Daphne**, maintained by the Django Channels project itself, is a
reference **ASGI** server — it speaks both plain HTTP and WebSocket
natively, using the exact same `config.asgi:application` object Stage 5
already wired up for local development (Channels' own `runserver`
override, used in dev). `entrypoint.prod.sh` runs:

```bash
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Gunicorn was removed from `requirements.txt` entirely once this became
clear — keeping an unused dependency around, especially one implying "this
is what serves your app" when it isn't, would only confuse whoever reads
this project next.

---

## 6. The frontend's multi-stage production build

### Why `next dev` (Stage 1's `frontend/Dockerfile`) isn't good enough here

`next dev` is a development server: it recompiles on every file change,
skips various optimizations, and ships a considerably larger, slower
runtime than what a real visitor's request needs to go through. None of
that belongs in a deployed environment.

### Reading `frontend/Dockerfile.prod`'s three stages

```dockerfile
FROM node:20-slim AS deps      # installs dependencies, cached separately
FROM node:20-slim AS builder   # runs `next build`, produces the compiled app
FROM node:20-slim AS runner    # the actual image that ships and runs
```

A **multi-stage build** lets earlier stages do heavy lifting (installing
every dev dependency, running the full build toolchain) without any of
that ending up in the final image — only the `COPY --from=builder ...`
lines at the bottom decide what actually survives into the image that
gets deployed and run. This is why the `runner` stage's final image is
dramatically smaller than simply copying the whole project and running
`npm start` directly.

### `output: "standalone"` (`next.config.js`)

```js
output: "standalone",
```

This tells Next.js's build process to trace through the *actual* code
paths used at runtime and copy only the `node_modules` packages genuinely
needed to run the compiled app into `.next/standalone/`, alongside a
generated `server.js` entrypoint — rather than needing the entire
`node_modules` folder (every dev dependency, every unused package)
present in the final container. This is what the `runner` stage's
`COPY --from=builder /app/.next/standalone ./` line depends on.

### Build-time vs. run-time environment variables

```dockerfile
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build
```

This is a genuinely easy-to-miss Next.js quirk worth calling out
explicitly: every backend environment variable in this project (JWT
secrets, database URLs, etc.) is read fresh each time the container
*starts* — completely ordinary runtime configuration. Next.js's
`NEXT_PUBLIC_*` variables are different: they get baked directly into the
compiled JavaScript bundle **during** `next build`, because that's the
only way client-side browser code (which can't read server environment
variables at all) ends up with the value. This means
`NEXT_PUBLIC_API_BASE_URL` has to be supplied as a Docker build argument
(`docker-compose.prod.yml`'s `build.args`), not a normal runtime
`environment:` entry the way every other service's config works — the
same value used elsewhere would silently have no effect if set as a
regular environment variable on the `frontend` service instead.

---

## 7. Glossary additions (Stage 6 terms)

- **Reverse proxy** — a server (Nginx, here) that sits in front of one or
  more backend applications and forwards requests to them, from the
  outside world's point of view acting as if it *is* the application.
- **TLS termination** — the point where an encrypted (HTTPS/WSS)
  connection is decrypted; everything "behind" that point can be plain,
  unencrypted traffic if it never leaves a trusted network.
- **Upstream** (Nginx) — a named group of one or more backend servers
  Nginx can proxy requests to.
- **WSGI vs. ASGI** — WSGI is Python's original, synchronous
  one-request-in-one-response-out web server interface; ASGI extends
  that to support asynchronous, long-lived connections like WebSockets.
- **Multi-stage Docker build** — splitting a `Dockerfile` into named
  stages so that heavy build-time tooling never ends up in the final,
  shipped image — only explicitly `COPY --from=<stage>`'d files survive.
- **`X-Forwarded-*` headers** — a set of conventional headers a reverse
  proxy adds so the application behind it can learn what the *original*
  request actually looked like (real client IP, original scheme).
- **HSTS** (HTTP Strict Transport Security) — a header telling browsers
  to always use HTTPS for a domain from now on, even before trying plain
  HTTP first.
