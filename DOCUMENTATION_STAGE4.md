# SkillSphere — Stage 4 Documentation

Continues from `DOCUMENTATION.md`, `DOCUMENTATION_STAGE2.md`, and
`DOCUMENTATION_STAGE3.md`. This stage adds full-text search via
Elasticsearch — conceptually the most "new technology" of any stage so
far, but also the one where the hexagonal architecture investment from
Stage 1 pays off most visibly (see section 5).

---

## 1. What Elasticsearch actually is, and why not just use the database

### The problem with `LIKE '%query%'` in Postgres

You could implement "search" with a plain SQL query:

```sql
SELECT * FROM projects_project WHERE title LIKE '%recipe%' OR description LIKE '%recipe%';
```

This works for tiny datasets but has real problems at any scale:

- **No relevance ranking** — every match is equally "good"; there's no
  concept of "this result matched the title, which matters more than
  matching the description."
- **No typo tolerance** — searching "recepie" finds nothing.
- **Slow at scale** — `LIKE '%...%'` (a leading wildcard) can't use a
  normal database index, so Postgres has to scan every row, checking each
  one by hand, which gets slower as your table grows.
- **No word-level matching** — "offline-first recipe app" wouldn't match
  a search for "recipe offline" (different word order) without a lot of
  manual query-building.

### What Elasticsearch is

Elasticsearch is a separate database, purpose-built for exactly this
problem. It's built around an **inverted index** — the same concept as a
book's index at the back: instead of "page 42 contains these words," it
stores "the word 'recipe' appears in documents 7, 19, 42, ..." This makes
"find every document containing this word" extremely fast, no matter how
big the dataset is, and it comes with relevance scoring, typo tolerance
(fuzzy matching), and word-level analysis built in.

### The tradeoff: two sources of truth

Using Elasticsearch means your data now lives in **two places**: Postgres
(the "real"/authoritative copy — what you'd restore from if you lost
everything) and Elasticsearch (a specialized, disposable *copy*, kept only
for fast searching). This is why:

- Every Elasticsearch document mirrors data that already exists in
  Postgres — nothing is ever stored *only* in Elasticsearch.
- The `reindex_search` management command exists specifically because
  Elasticsearch's copy can be wiped and rebuilt from Postgres at any time
  — it's disposable by design.
- If Elasticsearch is down, the rest of the app (auth, uploads,
  notifications, dashboards) keeps working fine — only search degrades
  (see section 4).

---

## 2. The indexing pipeline: from an upload to a searchable document

```
 User uploads a file
        │
        ▼
 ProjectUploadView creates the Project row (status: "pending")
        │
        ▼
 process_uploaded_project_task (Stage 2) runs in the background:
   - marks "processing"
   - checksums the file
   - marks "ready"
        │
        ▼
 index_project_task.delay(project_id)   ◄── Stage 4 addition
        │
        ▼
 Elasticsearch now has a searchable copy of this project
```

### Why index *after* processing, not at upload time

`index_project_task` is triggered from inside `process_uploaded_project_task`
(Stage 2's task), specifically right after the status flips to `"ready"` —
not from `ProjectUploadView` itself. This matters: a project that's still
`"pending"` or `"processing"`, or one that got `"rejected"` (the file
couldn't be read), should never show up in someone else's search results.
Tying indexing to the *same* place that marks something `"ready"` makes
that guarantee structural rather than something every call site has to
remember to check.

### Why indexing is a Celery task and not inline

Same reasoning as Stage 2's welcome emails: talking to Elasticsearch over
the network is exactly the kind of "shouldn't block the response" work
Celery exists for. If Elasticsearch is briefly slow, the person uploading
a file shouldn't feel that at all.

### `ProjectDocument` — a deliberately "denormalized" shape

```python
@dataclass
class ProjectDocument:
    id: UUID
    title: str
    description: str
    tags: list[str]
    owner_id: UUID | None
    owner_username: str  # <- the actual username, not just an owner_id
    status: str
```

In Postgres, you'd never duplicate a username onto the `Project` table —
that's what the `owner` foreign key is for, and duplicating it would risk
it going stale if the user ever renamed themselves. But a search
document works differently: it's read many times and written once per
project, and every read needs to render fast, standalone results (a
title, an owner name, tags) without doing a second database lookup per
search result. This tradeoff — trading normalization for read speed — is
completely normal for a search/reporting index, and is a smaller-scale
example of the same "read models can bend the usual rules" idea Stage 3
introduced for the `analytics` app.

---

## 3. The `Tag` model

```python
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Project(models.Model):
    ...
    tags = models.ManyToManyField(Tag, related_name="projects", blank=True)
```

A many-to-many relationship, because one project can have several tags
("django", "api", "portfolio") and one tag ("django") is shared across
many projects — a plain `ForeignKey` (one project → one tag) wouldn't fit.

### Why tags are lowercased and deduplicated via `get_or_create`

```python
tag_objects = [
    Tag.objects.get_or_create(name=name.strip().lower())[0]
    for name in tags
    if name.strip()
]
project.tags.set(tag_objects)
```

`get_or_create()` either finds an existing `Tag` row with that name, or
creates a new one — either way, you get back a real `Tag` object. Without
lowercasing, `"Django"` and `"django"` would become two different tag
rows even though they mean the same thing to a person searching. Doing
this normalization once, at write time (upload), is much simpler than
trying to handle it every time someone searches.

### Why tags are set *after* `project.file.save(...)`, not before

A many-to-many relationship needs both sides to already exist in the
database (Django has to insert rows into a hidden join table linking the
project's ID to each tag's ID) — so the `Project` row has to be saved
first. This is why `repositories.py`'s `create()` method calls
`project.file.save(file_name, file, save=True)` (which saves the whole
project row, including triggering the ID-based upload path from Stage 2)
*before* calling `project.tags.set(...)`.

---

## 4. Graceful degradation when Elasticsearch is down

### The domain exception: `SearchUnavailableError`

```python
except _ES_ERRORS as exc:
    raise SearchUnavailableError("Search index is unreachable") from exc
```

`ElasticsearchProjectSearch`/`ElasticsearchUserSearch` catch the
Elasticsearch client library's own connection-related exceptions
(`ConnectionError`, `ConnectionTimeout`, `TransportError`) and re-raise
them as our own domain-level `SearchUnavailableError`. This matters for
the same reason Stage 1's domain exceptions did: the API layer
(`api/views.py`) only needs to know about *our* exception type to decide
what HTTP status to return — it doesn't need to import anything from the
`elasticsearch` library at all, keeping that dependency contained entirely
within the infrastructure layer.

```python
try:
    results = service.search(query)
except SearchUnavailableError:
    return Response({"detail": "Search is temporarily unavailable"}, status=503)
```

**503 Service Unavailable**, not 500. A 500 says "something is broken in
our code." A 503 says "this specific dependency is temporarily down, try
again shortly" — a meaningfully different, more honest signal to whatever
is calling the API (including, eventually, a frontend that could show
"search is taking a break" instead of a scary generic error).

### Why indexing tasks retry, but search requests don't

`index_project_task`/`index_user_task` use Celery's retry mechanism
(`self.retry(exc=exc)`, up to 5 attempts) — if Elasticsearch happens to be
mid-restart when a project finishes processing, the indexing job will
simply try again a few times rather than permanently losing that project
from search. A live search *request*, on the other hand, has an actual
person waiting on the other end — retrying it silently for 15+ seconds
would be a worse experience than just telling them "try again shortly"
immediately.

---

## 5. Testing without a real Elasticsearch server — the hexagonal payoff

### The situation

Spinning up a full Elasticsearch server just to run `pytest` would be
slow, heavyweight, and fragile (tests failing because a Java process
hadn't finished booting yet, for example) — not something you want in a
fast local test loop or a CI pipeline that runs on every commit.

### The solution: a second, fake adapter

```python
class InMemoryProjectSearch(ProjectSearchPort):
    def __init__(self):
        self._documents: dict[str, ProjectDocument] = {}

    def index_project(self, document: ProjectDocument) -> None:
        self._documents[str(document.id)] = document

    def search_projects(self, query: str, limit: int = 20) -> list[ProjectSearchResult]:
        ...  # naive substring match over an in-memory dict
```

`apps/search/tests/test_search_services.py` imports **this** class, not
`ElasticsearchProjectSearch`, and passes it into
`IndexProjectService`/`SearchProjectsService` exactly the way the real API
views pass in the real Elasticsearch adapter. Because both classes
implement the same `ProjectSearchPort` interface, the application-layer
services (`IndexProjectService`, `SearchProjectsService`) can't tell the
difference — and neither can the test.

**This is precisely the point of dependency inversion**, explained back
in Stage 1's documentation for `RegistrationService`/`UserRepository`: the
application layer only ever depends on an abstract port, never on a
specific real implementation. Stage 4 is where that investment clearly
pays for itself — you get fast, reliable, zero-infrastructure tests for
real business rules (tag matching, "don't surface non-ready projects",
"a blank query returns nothing") without needing Elasticsearch, Docker, or
network access at all.

### What this *doesn't* test

The in-memory fake proves the **application logic** is correct. It does
**not** prove that `ElasticsearchProjectSearch`'s actual Elasticsearch
query syntax (the `multi_match`/`fuzziness`/`filter` body sent to the real
server) is correct — that can only be verified against a real running
Elasticsearch instance. This is an honest limitation, not a gap that was
missed: this environment can't run a real Elasticsearch server to verify
that piece end-to-end, so it was written carefully against the
`elasticsearch-py` 7.17 client's documented API, but **you should smoke-test
it yourself** once you have `docker compose up` running:

```bash
# after registering a user and uploading + waiting for a project to reach "ready"
curl "http://localhost:8000/api/v1/search/projects/?q=recipe"
curl "http://localhost:8000/api/v1/search/users/?q=amy"

# check Elasticsearch directly, bypassing the API:
curl http://localhost:9200/_cat/indices?v
curl http://localhost:9200/skillsphere_projects/_search?pretty
```

---

## 6. Why Elasticsearch 7.17, not 8.x

Elasticsearch 8.x enables security (TLS, passwords) by default, which
means extra setup (generating certificates, handling an auto-generated
elastic user password, configuring the Python client to trust the
certificate) just to get a local dev environment running. Elasticsearch
7.17 (the last 7.x release) runs with security disabled by a single
environment variable (`xpack.security.enabled: "false"` in
`docker-compose.yml`) and no other setup — the right tradeoff for a local
learning/dev environment, though **not** a configuration you'd want to
carry into a real production deployment with a real domain and real
users' data. The Python client version (`elasticsearch==7.17.13`) is
pinned to match the server's major version — the client and server
libraries generally aren't compatible across major version boundaries.

---

## 7. Search permissions: why it's public (`AllowAny`)

Every other Stage 1–3 endpoint requires a Bearer access token. Search is
the one deliberate exception:

```python
# Search is intentionally public (AllowAny) - browsing what others have
# built doesn't require an account, matching the "explore others' work"
# goal from the project brief. Downloading still requires auth.
```

This mirrors how most real platforms work (GitHub lets you search/browse
public repos without an account, but cloning/downloading privately-scoped
things still requires being logged in). The Elasticsearch query itself
also filters to `status: "ready"` projects only — so even without auth,
nobody can search their way into seeing someone else's still-processing
or rejected upload.

---

## 8. Glossary additions (Stage 4 terms)

- **Inverted index** — Elasticsearch/Lucene's core data structure: a
  mapping from *words* to *which documents contain them*, the opposite
  direction from how a normal database table is organized, and what
  makes full-text search fast.
- **Fuzziness** (`"fuzziness": "AUTO"`) — lets a search match close
  misspellings (e.g. "recepie" still finds "recipe") within a small edit
  distance, automatically scaled based on the search term's length.
- **Analyzer/tokenizer** — Elasticsearch's process for breaking text into
  searchable words (tokens) and normalizing them (lowercasing, etc.)
  before indexing — this is what makes word-level, order-independent
  matching possible, unlike SQL's `LIKE`.
- **Read model / denormalization** — deliberately duplicating data (like
  `owner_username` inlined into `ProjectDocument`) to make reads fast,
  accepted specifically because a search index is a disposable, rebuildable
  copy, not the source of truth.
- **Test double / fake** — a simplified stand-in for a real dependency
  (here, `InMemoryProjectSearch` standing in for real Elasticsearch),
  useful specifically because both share the same interface (port).
