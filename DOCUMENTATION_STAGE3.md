# SkillSphere — Stage 3 Documentation

Continues from `DOCUMENTATION.md` (Stage 1) and `DOCUMENTATION_STAGE2.md`
(Stage 2). This stage is smaller conceptually than Stage 2 — one new
backend app, three real frontend pages — but introduces a genuinely
important architectural idea: **when it's correct to break your own
layering rules on purpose.**

---

## 1. The `analytics` app — and why it's allowed to "cheat"

### The problem

A dashboard needs to answer questions like "how many projects does this
user have, broken down by status, plus their download count, plus their
unread notification count, plus a 14-day activity trend" — all in one
response. Those numbers live in **four different bounded contexts**:
`Project` (projects app), `Notification` (notifications app),
`ActivityLog` (activity app), and `User` (users app).

If we followed Stage 1/2's pattern strictly, `analytics` would need to
ask each app's own repository for its data, then stitch the results
together — e.g. call `DjangoProjectRepository.list_for_owner()`,
`DjangoNotificationRepository.list_for_user()`, etc., and compute counts
in Python. That works, but it means pulling potentially large datasets
into Python memory just to count/group them — exactly the kind of thing
a database is *much* better at doing directly (`Count()`, `Sum()`,
`GROUP BY`).

### The resolution: CQRS-style read models

**CQRS** (Command Query Responsibility Segregation) is the idea that the
model you use to *change* data (commands: register, upload, mark-read —
all the stuff Stage 1/2's application services do) doesn't have to be the
same model you use to *read* data for reporting. Reporting/read-only
queries are commonly allowed to cut across bounded contexts and talk to
the database directly, because:

- They don't mutate anything, so there's no risk of business rules being
  bypassed (the domain layer's whole job is protecting *writes*).
- Aggregation (counting, grouping, summing) is something the database
  engine is fundamentally better at than an in-memory Python loop.

So `apps/analytics/infrastructure/django/queries.py`
(`DjangoAnalyticsQueries`) directly imports the ORM models from three
other apps:

```python
from apps.activity.infrastructure.django.models import ActivityLog
from apps.notifications.infrastructure.django.models import Notification
from apps.projects.infrastructure.django.models import Project
from apps.users.infrastructure.django.models import User
```

This is the *only* place in the whole codebase where one app's
infrastructure layer imports another app's models directly. Everywhere
else (Stage 1, Stage 2), each app only ever touches its own table. The
`AnalyticsQueryPort` docstring calls this out explicitly so it doesn't
read as an accidental layering violation to someone reading the code
later — it's a deliberate, named exception.

**Why still bother with domain/application/port layers here at all**,
if it's "just queries"? Two reasons: (1) consistency — every other app in
this codebase follows the same shape, so a new contributor already knows
where to look; (2) it still buys you the same testability benefit — the
`BuildUserDashboardService`/`BuildAdminDashboardService` application
classes depend on the abstract `AnalyticsQueryPort`, so you could swap in
a fake/test double for either service without touching real data, exactly
like Stage 1's `RegistrationService`.

---

## 2. The dashboard queries, explained

### `_daily_counts()` — turning rows into a chart-ready trend

```python
rows = (
    queryset.filter(created_at__gte=since)
    .annotate(day=TruncDate("created_at"))
    .values("day")
    .annotate(count=Count("id"))
    .order_by("day")
)
```

Step by step:
- `TruncDate("created_at")` — a database function that strips the time
  portion off a timestamp, leaving just the date. `annotate(day=...)`
  attaches that truncated date as a virtual column on each row.
- `.values("day")` — tells Django "group by this column" (this is the SQL
  `GROUP BY` under the hood).
- `.annotate(count=Count("id"))` — after grouping, count how many rows
  fell into each group.
- `.order_by("day")` — oldest to newest.

This gives you real rows like `{"day": date(2026, 7, 10), "count": 3}` —
but only for days that actually *had* activity. A chart with gaps looks
broken, so the rest of the function fills in **every day in the trailing
14-day window with `count: 0`** if nothing happened that day, using a
plain Python dict lookup (`counts_by_day.get(day, 0)`). This is a common
pattern any time you're building a time-series chart from sparse data.

### Why `total_downloads` uses `Sum`, not `Count`

```python
total_downloads = projects.aggregate(total=Sum("download_count"))["total"] or 0
```

Each `Project` row already stores its own running `download_count`
(incremented atomically on every download — see section 3). So getting a
user's *total* downloads across all their projects means **summing** that
column, not counting rows. The `or 0` handles the case where a user has
zero projects at all — `Sum()` on an empty queryset returns `None` in
Django, not `0`, which would otherwise show up as `null` in the API
response instead of a sensible `0`.

### The admin dashboard's "most active users" query

```python
top_users = (
    ActivityLog.objects.exclude(user_id=None)
    .values("user__username")
    .annotate(action_count=Count("id"))
    .order_by("-action_count")[:5]
)
```

`.values("user__username")` groups activity log rows by the *related*
user's username (Django automatically joins across the foreign key for
you — you never write raw SQL `JOIN` here). `.exclude(user_id=None)`
drops anonymous/unauthenticated requests, since "most active anonymous
visitor" isn't a meaningful ranking. `[:5]` limits it to the top 5 —
Django translates a Python slice on a queryset into a SQL `LIMIT`, so this
never fetches more rows from the database than it needs.

### Permission check: `IsAdminUser`

```python
permission_classes = [IsAuthenticated, IsAdminUser]
```

DRF's built-in `IsAdminUser` checks `request.user.is_staff`. This is
Django's own built-in staff flag (the same one that controls whether a
user can log into `/admin/`) — no custom permission class needed. Listing
both `IsAuthenticated` and `IsAdminUser` means: first confirm there's a
real logged-in user at all (clearer 401 for anonymous requests), then
confirm they're staff (403 otherwise) — DRF checks permission classes in
order and stops at the first failure.

---

## 3. Atomic download counting

```python
Project.objects.filter(id=project_id).update(download_count=F("download_count") + 1)
```

`F("download_count")` is Django's way of saying "whatever this column's
current value is *in the database*, right now" — as opposed to reading
the value into Python, adding 1, and writing it back (`project.download_count
+= 1; project.save()`), which has a subtle bug under concurrent requests:
if two people download the same file at almost the same instant, both
could read the same starting value (say, 5), both compute 6, and both
write 6 back — one download gets silently lost. Using `F()` pushes the
`+1` into the actual SQL `UPDATE` statement (`UPDATE ... SET
download_count = download_count + 1`), which the database itself
guarantees is atomic — no lost updates, no matter how many simultaneous
downloads happen.

---

## 4. Frontend: the shared `AppShell`

### Why a shared shell component

`/dashboard`, `/projects`, and `/notifications` all need the same sidebar
(nav links, dark mode toggle, logout, unread badge). Rather than copy
that markup into all three pages, `components/AppShell.tsx` wraps whatever
page content is passed as `children` — this is the standard React
"layout component" pattern (distinct from Next.js's special `layout.tsx`
files, which wrap *every* route including public ones like `/login`;
`AppShell` is opt-in, only used by the authenticated pages).

### Dark mode: why `localStorage` here, but never for auth tokens

Stage 1's documentation explained why the *access token* must never touch
`localStorage` (readable by any injected script, i.e. XSS-vulnerable).
Dark mode preference has no security implications at all — worst case an
attacker's script could... know your color scheme preference. So
`hooks/useDarkMode.ts` uses `localStorage` freely, plus
`window.matchMedia("(prefers-color-scheme: dark)")` to default to the
user's OS-level preference the very first time they visit, before they've
ever toggled anything themselves.

```js
document.documentElement.classList.toggle("dark", initial);
```

This adds/removes a `"dark"` class directly on the `<html>` tag. Combined
with `darkMode: "class"` in `tailwind.config.js` (set back in Stage 1),
this is what makes every `dark:bg-...`/`dark:text-...` utility class
throughout the app activate or deactivate together.

### The download button: why it's not a plain `<a href>`

A normal link (`<a href="/api/v1/projects/.../download/">`) would send a
plain browser GET request with no `Authorization` header attached — the
backend would reject it with 401, since (per Stage 1's design) the access
token lives only in memory and is attached manually by Axios's request
interceptor, not sent automatically by the browser like a cookie would be.

`lib/projects.ts: downloadProject()` instead:
1. Calls the endpoint via the same authenticated `api` Axios instance
   (`{ responseType: "blob" }` tells Axios to expect binary file data, not JSON).
2. Turns the returned binary blob into a temporary browser-local URL
   (`URL.createObjectURL`).
3. Creates an invisible `<a>` tag pointing at that temporary URL, clicks it
   programmatically (triggering the browser's normal "save file" behavior),
   then immediately removes the tag and revokes the temporary URL to free
   the memory it was using.

### Drag-and-drop upload

```jsx
<label
  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
  onDragLeave={() => setIsDragging(false)}
  onDrop={handleDrop}
>
  <input type="file" className="hidden" onChange={...} />
</label>
```

Two things worth noting: (1) `onDragOver` **must** call
`e.preventDefault()` — browsers block dropping by default (e.g. dropping a
file usually just opens it in a new tab instead), and calling
`preventDefault()` in `onDragOver` is what tells the browser "this element
accepts drops." (2) Wrapping a visually-hidden real `<input type="file">`
inside a styled `<label>` is a common accessibility-friendly pattern —
clicking anywhere on the pretty drop-zone actually clicks the real
(invisible) file input underneath, giving you both drag-and-drop *and* a
normal "click to browse" experience for free, from one element.

### Recharts: what `ResponsiveContainer` is for

```jsx
<div className="h-56">
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={stats.activity_last_14_days}>...</LineChart>
  </ResponsiveContainer>
</div>
```

Recharts' `<LineChart>` needs explicit pixel dimensions to render its SVG
— it doesn't know how to "just fill available space" on its own.
`<ResponsiveContainer>` solves this by measuring its *parent* element (the
`div.h-56` here) and re-rendering the chart at that exact size, including
on window resize. This is why the height is set with a plain Tailwind
class on the wrapping `div`, not as a prop on the chart itself.

---

## 5. What's genuinely NOT done yet (be upfront about this)

- **Content-type sniffing for uploads** (still flagged from Stage 2 — the
  browser-declared MIME type is trusted, not verified against actual file
  bytes).
- **Next.js dependency vulnerabilities**: `npm audit` currently flags a
  few moderate/high-severity advisories against Next.js 14.2.35 (the
  newest available patch on the 14.x line) that are only fixed by
  upgrading to Next 15/16 — a breaking change deliberately out of scope
  here so as not to destabilize three stages of working frontend code at
  once. Worth doing as a deliberate, tested upgrade before any real
  deployment.
- **No server-side route protection** on `/dashboard`, `/projects`,
  `/notifications` — they redirect to `/login` client-side if there's no
  user in the Zustand store, but a determined visitor with dev tools open
  could briefly see the page shell render before the redirect kicks in
  (no sensitive data is actually fetched or shown before the check runs,
  but it's not a true server-enforced boundary). A production app would
  eventually want Next.js middleware checking auth state before the page
  even renders.

---

## 6. Glossary additions (Stage 3 terms)

- **CQRS** (Command Query Responsibility Segregation) — using a different
  model/path for reads (queries) than for writes (commands); read models
  are commonly allowed to break strict layering rules since they can't
  corrupt data.
- **Read model** — a data shape built specifically to answer a question
  efficiently (e.g. "counts by status"), as opposed to the domain model
  used to enforce business rules on writes.
- **`F()` expression** (Django) — a reference to a database column's
  current value, used to build atomic `UPDATE ... SET x = x + 1`-style
  statements instead of racy read-modify-write code in Python.
- **`TruncDate`** — a Django ORM database function that truncates a
  datetime down to just its date, commonly used for "group by day"
  reporting queries.
- **Layout component** (React) — a component that wraps `children` to
  provide shared UI (nav, sidebar, etc.) across multiple pages, as
  distinct from Next.js's file-based `layout.tsx` convention.
