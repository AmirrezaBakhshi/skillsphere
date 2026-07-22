# SkillSphere — Stage 5 Documentation

Continues from `DOCUMENTATION.md`, `DOCUMENTATION_STAGE2.md`,
`DOCUMENTATION_STAGE3.md`, and `DOCUMENTATION_STAGE4.md`. This is the
most infrastructure-heavy stage yet — real-time WebSocket communication —
and also the stage where two genuine bugs were caught and fixed during
development (see section 6). Worth reading that section closely: it's a
realistic look at what "testing your own code" actually catches.

---

## 1. Why WebSockets, and what Django Channels adds

### The limitation of plain HTTP

Every endpoint built in Stages 1–4 follows the same shape: the client
sends one request, the server sends back one response, and the
connection closes. That's fine for "upload a file" or "list my
notifications," but it can't do "the moment someone sends me a message,
show it on my screen immediately" — plain HTTP has no way for the
*server* to push something to the client without the client asking first
(polling repeatedly is the old workaround, and it's wasteful and laggy).

**WebSockets** solve this: after an initial handshake (which starts as a
normal HTTP request), the connection stays open, and either side can send
data to the other at any time, for as long as the connection lasts.

### Why Django needs Channels for this

Plain Django (WSGI) is built entirely around the request-response cycle —
a view function runs, returns a response, and is done. It has no concept
of "a connection that stays open." **Django Channels** extends Django to
run on **ASGI** instead (Asynchronous Server Gateway Interface), which
supports long-lived connections as a first-class concept, alongside
regular HTTP. This is exactly why Stage 1's `config/asgi.py` already
existed with a comment reserving this spot — the groundwork was laid four
stages ago specifically for this moment.

### The `ProtocolTypeRouter`

```python
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
```

This is the top-level ASGI application. It looks at what *kind* of
connection just came in — a normal HTTP request or a WebSocket handshake —
and routes each to a completely different pipeline. HTTP still goes
through ordinary Django (`django_asgi_app` — the exact same views,
middleware, and URL routing built in every previous stage, completely
unchanged). Only WebSocket connections go through Channels' own routing
and our custom JWT middleware.

### Consumers: the WebSocket equivalent of a view

`apps/chat/infrastructure/channels/consumers.py: ChatConsumer` is
conceptually a DRF `APIView`'s WebSocket counterpart — except instead of
one method per HTTP verb, it has lifecycle methods: `connect()` (runs
once, when the connection opens), `receive_json()` (runs every time the
client sends something), and `disconnect()` (runs once, when the
connection closes, for any reason). One `ChatConsumer` **instance** exists
per open connection — unlike a Django view, which is stateless per
request, a consumer can hold state (like `self.conversation_id`) for the
entire lifetime of that one connection.

### Groups: how one message reaches multiple people

```python
await self.channel_layer.group_add(self.group_name, self.channel_name)
...
await self.channel_layer.group_send(self.group_name, {...})
```

Every open connection has a unique `channel_name`. A **group** is just a
named set of channel names — here, one group per conversation
(`conversation_<uuid>`), so every participant currently viewing that
conversation is in the same group. `group_send()` fans a message out to
every channel currently in that group — this is literally the mechanism
that makes "the other person sees your message instantly" work.

### Why Redis, specifically (the "channel layer")

The group membership and message fan-out described above have to be
tracked *somewhere* shared, because in a real deployment you'd typically
run **more than one** Django/Channels process (for capacity) — and two
people in the same conversation could easily have their WebSocket
connections handled by two completely different server processes. A
plain Python dictionary in memory wouldn't be visible across processes.
Redis, acting as the **channel layer** backend (`CHANNEL_LAYERS` setting,
`channels_redis` package), is what makes group membership and message
delivery work correctly *even across multiple server processes* — the
same reason Redis was already doing double duty as Stage 2's Celery
broker; it's a natural fit for this too.

---

## 2. Authenticating a WebSocket: the JWT-in-query-string pattern

### The problem

A browser's native WebSocket API (`new WebSocket(url)`) has no way to
attach custom headers like `Authorization: Bearer <token>` — unlike
`fetch`/Axios, which Stage 1 relies on entirely for REST auth. The
handshake is a single browser API call with just a URL; there's no
headers parameter.

### The solution used here

```
ws://.../ws/chat/<conversation_id>/?token=<access_token>
```

The same short-lived access token used everywhere else gets passed as a
query string parameter instead of a header. `apps/chat/infrastructure/
channels/jwt_auth_middleware.py: JWTAuthMiddleware` reads it off the
connection's query string, validates it using `simplejwt`'s own
`AccessToken` class (the exact same validation logic — signature, expiry —
that every REST request already goes through via
`CookieJWTAuthentication`, just invoked directly here instead of through
DRF), and sets `scope["user"]` accordingly — the WebSocket world's
equivalent of `request.user`.

### Is putting a token in a URL a security downgrade?

It's a fair question, and worth being honest about: URLs (including query
strings) can end up in server logs, browser history, or a `Referer`
header in ways that a header wouldn't. Two things limit the actual risk
here: (1) the *access* token, not the long-lived refresh token, is what's
used — the same 15-minute-lifetime token from Stage 1, so exposure has a
narrow time window; (2) this is a `wss://` connection in any real
deployment (encrypted, same as `https://`), so the token isn't visible
in transit, only potentially in places that log full request URLs
server-side. This is a widely-used, pragmatic pattern for browser-based
WebSocket auth precisely because the browser API leaves no better option
— but it's worth knowing the tradeoff rather than treating it as
risk-free.

### Why the frontend builds this URL where it does

```typescript
export function buildChatSocketUrl(conversationId: string): string {
  ...
  const token = useAuthStore.getState().accessToken ?? "";
  return `${wsBase}/ws/chat/${conversationId}/?token=${encodeURIComponent(token)}`;
}
```

This is the **one and only place** in the entire frontend where the
access token leaves the Zustand store as anything other than an Axios
request header (see Stage 1's documentation on why the token lives in
memory only). It's still never written to `localStorage` or a cookie —
it's read from memory, used to build one URL, for one connection attempt,
and that's it.

---

## 3. Why the conversation model is deliberately simple

```python
class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    project = models.ForeignKey("projects.Project", ..., null=True, blank=True)
```

This models **1:1 direct messages** (exactly two participants) plus an
optional link to a project (for a future "message the owner about this
upload" feature) — it deliberately does **not** attempt to model group
chats, read receipts, typing indicators, or message editing. Those are
straightforward extensions of the same pattern (more participants in the
M2M, additional fields on `Message`) but were left out to keep this stage
focused on the core real-time mechanism, which is the genuinely new,
hard-to-learn concept here.

### `SendMessageService` — one place, two callers

```python
@dataclass
class SendMessageService:
    def send(self, *, conversation_id, sender_id, body):
        ...  # validation + participant check + persistence
```

Both `ChatConsumer.receive_json()` (the WebSocket path) and
`ConversationMessagesView.post()` (the REST fallback) call this exact
same application-layer service — this is the same hexagonal-architecture
payoff from Stage 1: business rules (message length limits, "you must be
a participant to send") live in exactly one place, so there's no risk of
the WebSocket path enforcing a rule the REST path forgot, or vice versa.

---

## 4. The recommendation engine: a deliberate, explainable design choice

### Why not a real ML model / LLM call

A production recommendation system might use collaborative filtering, a
trained embedding model, or an LLM call. None of those fit well here:
- A trained model needs a meaningful amount of historical interaction
  data to be better than a simple heuristic — a brand-new platform with a
  handful of test users has none.
- An LLM-based recommender would need an API key and external network
  calls for every dashboard load, adding cost, latency, and a new failure
  mode, for a feature that's explicitly a "bonus."
- Both would be considerably harder to write deterministic, fast unit
  tests for — which matters a lot for a learning project where you want
  to be able to reason about *why* a recommendation happened.

### What was built instead: tag/text similarity

```python
tag_score = _jaccard(my_tags, project_tags)
text_score = _jaccard(my_words, project_words)
score = self.tag_weight * tag_score + self.text_weight * text_score
```

**Jaccard similarity** — `|intersection| / |union|` of two sets — is a
simple, standard way to measure how much two sets overlap, here applied
to (a) the tags across a user's own projects vs. a candidate project's
tags, and (b) the meaningful words in their titles/descriptions (after
stripping common "stopwords" like "the," "app," "project" that would
otherwise dominate every comparison without adding signal). Tags are
weighted higher (`tag_weight=0.8`) than text overlap (`text_weight=0.2`)
because a shared explicit tag ("django") is a much stronger, more
deliberate signal than two descriptions happening to share ordinary
words.

**This produces an explainable result** — every recommendation comes with
a `reason` field ("Shares tags with your projects: django, api") built
directly from the same data used to compute the score. This is a genuine
advantage a black-box model wouldn't give you for free.

### The cold-start fallback

```python
if not my_projects:
    return self._popularity_fallback(other_projects, limit)
```

A user with zero projects of their own has no "taste profile" to compare
anything against — Jaccard similarity against an empty set is
meaningless (and the code explicitly returns `0.0` for that case, see
`_jaccard()`). Rather than showing nothing, the fallback ranks by
`download_count` (from Stage 3) — "what's popular right now" is a
reasonable default recommendation for someone with no history, and is
exactly what most real platforms do for brand-new accounts.

### `ProjectCatalogPort` — yet another intentional cross-context read

Following Stage 3's `AnalyticsQueryPort` and Stage 4's search adapters,
`ProjectCatalogPort` is a third example of the same pattern: a read-only
view that reaches across into another app's data (`projects`) for
reporting/recommendation purposes, kept as its own narrowly-scoped
abstraction rather than reusing `apps.projects.domain.ports.
ProjectRepository` (which is about *owning and mutating* a single user's
own projects — a meaningfully different concern from "read a catalog of
everyone's ready projects").

---

## 5. Testing a WebSocket consumer

### `WebsocketCommunicator` — Channels' test client

```python
communicator_a = WebsocketCommunicator(application, f"/ws/chat/{conversation_id}/?token={access_a}")
connected_a, _ = await communicator_a.connect()
await communicator_a.send_json_to({"body": "hey devon!"})
response = await communicator_a.receive_json_from()
```

This is Channels' equivalent of DRF's `APIClient` — it simulates a real
WebSocket client against the actual `application` (the same
`ProtocolTypeRouter` used in production), without needing a real browser
or a real running server. The test in
`apps/chat/tests/test_chat_consumer.py` opens **two** simulated
connections (one per user), sends a message from one, and asserts **both**
sides receive it — this is what actually proves the group-broadcast
mechanism works, not just that a single connection can send/receive.

### Why this test genuinely needs real Redis (unlike Stage 4's fakes)

Stage 4's search tests got away with an in-memory fake standing in for
Elasticsearch, because `ProjectSearchPort` is *our own* abstraction — we
control both sides of that interface. The channel layer's group broadcast
mechanism is not something we wrote; it's Channels' own internal
implementation, and swapping it for a fake would mean not actually
testing the real fan-out behavior at all. A local Redis instance
(pointed to via `REDIS_URL`) is a small, fast, genuinely necessary
dependency for this one test file — this is a deliberate, documented
exception to "tests shouldn't need external services," not an oversight.

### `pytest-asyncio` and `asyncio_mode = auto`

Consumer test functions are `async def` (since `WebsocketCommunicator`'s
methods are all `await`-based, matching Channels' fully async design).
`pytest-asyncio`'s `asyncio_mode = auto` setting (in `pytest.ini`) tells
pytest to automatically run any `async def test_...` function inside an
event loop, without needing to mark every single one with
`@pytest.mark.asyncio` by hand.

---

## 6. Two real bugs found and fixed while building this stage

Worth documenting honestly, since finding and fixing bugs like these is
itself the point of writing tests, and it's useful to see what that
process actually looks like rather than only ever seeing polished
"it just worked" code.

### Bug 1: the "find existing direct conversation" query was silently broken

The first version of `get_or_create_direct_conversation` looked like this:

```python
existing = (
    Conversation.objects.filter(project=None, participants__id=user_a_id)
    .filter(participants__id=user_b_id)
    .annotate(participant_count=Count("participants"))
    .filter(participant_count=2)
    .first()
)
```

This looks reasonable, but a test (`test_start_conversation_creates_and_
is_idempotent` — calling "start a conversation" twice and asserting both
calls return the *same* conversation) caught that it always created a
**new** conversation every time, never finding the existing one. The root
cause: chaining two separate `.filter(participants__id=...)` calls on a
many-to-many field creates two separate SQL joins to the same related
table (this is standard, correct Django behavior for *that* part — it's
what lets you say "has a participant matching A, independently AND has a
participant matching B"). But adding `Count("participants")` *after*
those two joins already exist counts across the resulting cross-join,
inflating the number in a way that never actually equals `2` for a real
2-participant conversation — so the `participant_count=2` filter matched
nothing, `existing` was always `None`, and a fresh conversation got
created on every single call.

**The fix**: fetch candidate conversations containing `user_a_id`, then
compare each candidate's actual participant set in plain Python:

```python
candidates = Conversation.objects.filter(project=None, participants__id=user_a_id)
for candidate in candidates:
    if set(candidate.participants.values_list("id", flat=True)) == {user_a_id, user_b_id}:
        return self._to_entity(candidate)
```

Simpler, and correct — at the scale of "one person's direct
conversations" (not millions of rows), comparing sets in Python is
perfectly fast and avoids a genuinely subtle, easy-to-get-wrong Django ORM
interaction between chained `.filter()` calls and `Count()` annotations
on a many-to-many field.

### Bug 2: a best-effort background task could (sometimes) break its caller

While testing, one call path — registering a user, which kicks off
`index_user_task.delay(...)` to add them to the search index — showed a
raw Elasticsearch connection error escaping all the way up into a test
assertion, breaking a completely unrelated request (registration itself).
This traced back to a genuine gap in Stage 4's `ensure_indices()`
function: it wrapped *most* Elasticsearch errors into our own
`SearchUnavailableError` (so the retry logic could catch them) but missed
wrapping connection failures during index creation specifically. On top
of that, Celery's `self.retry()` behaves differently when a task runs
**eagerly** (synchronously, as in tests, with `CELERY_TASK_ALWAYS_EAGER
=True`) versus with a real worker and broker: with no real broker to
defer the retry to, `self.retry()` can only raise immediately rather than
actually rescheduling the task — which meant a best-effort, fire-and-
forget background action (indexing a new user for search) could, only in
this synchronous test/debug mode, end up failing the very request that
queued it.

**The fix** was two-fold:
1. `ensure_indices()` now wraps Elasticsearch connection errors into
   `SearchUnavailableError` too, consistently with every other method in
   the adapter (see `apps/search/infrastructure/elasticsearch/indices.py`).
2. The search-indexing tasks now catch *any* exception coming out of
   `self.retry()` itself and just log a warning instead of letting it
   propagate — because a search-indexing task, specifically, should never
   be able to break whatever queued it, in any execution mode. With a
   real worker in real deployment, `.delay()` already fully decouples
   the caller from the task's eventual outcome; this fix makes that same
   guarantee hold even when running eagerly.

**Why mention this at all?** Because it's a realistic example of exactly
the kind of thing integration testing (in this case, specifically testing
across two different subsystems — chat and search — interacting through
shared infrastructure) is supposed to catch, and it's more useful to see
that this project has bugs that get found and fixed like any real
codebase does, rather than presenting a version of events where
everything simply worked on the first attempt.

---

## 7. Glossary additions (Stage 5 terms)

- **WebSocket** — a persistent, two-way connection between client and
  server (unlike HTTP's one request → one response model), used here for
  real-time chat.
- **ASGI** (Asynchronous Server Gateway Interface) — the modern
  successor to WSGI that supports long-lived connections like WebSockets,
  alongside regular HTTP.
- **Consumer** (Channels) — the WebSocket equivalent of a Django view;
  one instance exists per open connection and can hold state for that
  connection's lifetime.
- **Channel layer** — the shared backend (Redis, here) that lets
  WebSocket connections handled by different server processes still
  coordinate group membership and message delivery.
- **Group** (Channels) — a named set of connections that a message can be
  broadcast to all at once (`group_send`) — the mechanism behind "everyone
  in this conversation sees the new message."
- **Jaccard similarity** — `|A ∩ B| / |A ∪ B|`, a simple, standard way to
  score how much two sets overlap; used here for tag- and word-based
  project similarity.
- **Cold start** (recommendation systems) — the problem of recommending
  something to a user with no history yet; commonly solved (as here) by
  falling back to overall popularity.
- **Eager mode** (Celery) — running a task synchronously in-process
  instead of via a real broker/worker; useful for tests, but changes how
  `self.retry()` behaves, as this stage's second bug demonstrates.
