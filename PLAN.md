# Build plan — from the current backend to the finished PWA

Companion to `trainingstracker_specs.md`. `UMBAU.md` describes how the backend
got to its current state; this file describes where it goes next.

Written in English because that is the language we work in now. The existing
German files (`UMBAU.md`, the code comments under `backend/app/`) stay German.

**Status (2026-09-04):** All phases done. 63 tests green, 43 endpoints,
Postgres migrated to head (`92d47e8a52d8`). Every screen is built, and the app
is installable on the iPhone over HTTPS from the tailnet.

---

## Decisions taken

| Question | Decision |
| --- | --- |
| Exercise scope | Per-user catalog, plans reference it via a join table |
| Progress metric | Best set weight, plus average reps, plus average weight when weighted |
| Bodyweight exercises | Reps only, no weight column |
| Month boundaries | Calendar months, always starting on the 1st |
| Month comparison | User picks both months from dropdowns |
| Active plan | Nullable FK on `appuser`, not a flag on the plan |
| Routing | By id (`/u/3`), name only displayed — names are not unique |
| Bodyweight progress | Average reps *and* best-set reps |
| Training days | A plan has N training days, each with a workout type ("Push") |
| Plan targets | Each planned exercise carries target sets + a rep range |
| Custom workouts | `training_day_id IS NULL`; excluded from analysis, shown in history |
| Custom exercise picker | Pick from catalog, or type a new name that joins the catalog |
| Workout picker | Lists the plan's training days ("Day 1 — Push"), plus Custom |
| Accent colour | Purple; regressions are not coloured, so red stays an error |
| Body weight in the log | `workout.body_weight`, snapshotted from `appuser.weight` |
| Active plan menu row | Dropped; switching moves into the plan list |
| Marking a session missed | One tap with undo, no dialog; plus backfill from the log |
| Rest timer | Not wanted |
| Offline workouts | Local draft, synced as one whole workout when online |

---

## Phase 0 — Commit what exists ✅ done

`pyproject.toml` and `uv.lock` are tracked, so a fresh clone can install the
project. `.DS_Store` and `__pycache__/main.cpython-314.pyc` were removed from
git and added to `.gitignore` (commit `3f56bf5`).

---

## Phase 1 — Data model ✅ done

### 1.1 Exercise becomes a per-user catalog

Today `exercise.workout_plan_id` is `NOT NULL`, so an exercise belongs to exactly
one plan. That breaks the progress comparison: "Bankdrücken" in the autumn plan
and "Bankdrücken" in the spring plan are two rows with two ids, and no join
connects them. The comparison would silently return nothing for every exercise.

```
appuser
  ├─ exercise                    (catalog, UNIQUE(user_id, title))
  └─ workout_plan
       └─< training_day          (position 1, type "Push")
             └─< training_day_exercise >── exercise
                                             ▲
          workout ──< exercise_set >─────────┘
```

- `exercise`: drop `workout_plan_id`, add `user_id` FK → `appuser` (CASCADE),
  `UNIQUE(user_id, title)`.
- `exercise_set` is unchanged — it already points at both `exercise_id` and
  `workout_id`, which is exactly what the aggregation needs.

### 1.2 Training days

A plan is not a flat exercise list. It has N training days per week, each with a
workout type such as "Push", "Pull" or "Legs", fixed when the plan is created.

- `training_day`: `workout_plan_id` FK (CASCADE), `position` integer,
  `workout_type` string. Free text, not an enum — splits vary too much
  (Upper/Lower, Arms, Full Body) to hard-code a list.
- `training_day_exercise`: `(training_day_id, exercise_id)` composite PK, plus
  `position`, `target_sets`, `target_reps_min`, `target_reps_max`. This is where
  "Bankdrücken 3×8-10" lives, so the live workout screen can show the target and
  prefill that many set rows instead of making you type each one.
- **Drop `workout_plan.training_days`.** The count is `COUNT(training_day)`;
  keeping the integer as well allows a plan that claims 4 but has 3 days.

### 1.3 Custom workouts

`workout.training_day_id`, nullable FK → `training_day`, `ON DELETE SET NULL`.
**`NULL` means custom** — no separate `is_custom` boolean. One column, one source
of truth; with two you can store a row claiming to be custom while pointing at a
training day.

A custom workout is entered when equipment is missing: the user picks exercises
freely (from the catalog, or types a new name which joins the catalog) and fills
in sets, reps and weight. It behaves like a normal workout except that the
analysis filters it out with `WHERE training_day_id IS NOT NULL`, while the
history view shows it labelled "Custom".

### 1.4 Exactly one active plan

`appuser.active_workout_plan_id`, nullable, FK → `workout_plan`, `ON DELETE SET NULL`.

A nullable FK makes "at most one" a structural guarantee. An `is_active` boolean
on the plan would allow two rows to be true at once and would need application
code or a partial unique index to prevent it.

This creates a circular FK between `appuser` and `workout_plan`. Alembic needs
`use_alter=True` on the constraint so it emits the `ALTER TABLE` after both
tables exist instead of deadlocking on creation order.

### 1.5 Migration and seed

Revision `ca67bbcf8314` covers all of the above and round-trips (verified
`upgrade` → `downgrade` → `upgrade` against Postgres). **No data migration:**
the database held only seed data, so the revision empties `exercise` rather
than guessing a `user_id` per row. `downgrade` empties it again, because the
exercise → plan assignment cannot be reconstructed once it is gone.

Two things the autogenerated draft got wrong and that were fixed by hand:
`exercise.user_id` was added `NOT NULL` to a table that still had rows, and the
new foreign keys were unnamed, so `downgrade`'s `drop_constraint(None, ...)`
could never have run.

`backend/scripts/seed.py` is rebuilt for the new model. It now produces a
per-user catalog, plans with training days and targets, an active plan per
user, a custom workout, and six months of history. Seed Ben deliberately keeps
**one** "Bankdruecken" across two plans (62.5 kg in the old, 85.0 kg in the
new) — the exact cross-plan case the comparison needs.

---

## Phase 2 — Training log ✅ done

This is the aggregation `UMBAU.md` §9.2 predicted would justify
`app/services/`. It is not CRUD, so it does not belong in a router.

```
GET /api/v1/users/{id}/log/workouts?skip=&limit=
GET /api/v1/users/{id}/log/months
GET /api/v1/users/{id}/log/progress?month_a=2025-09&month_b=2026-04
```

- `/log/workouts` — flat history, newest first: date, duration, plan title,
  set count, attended flag. This is spec view one.
- `/log/months` — the months that actually contain workouts, descending. The two
  dropdowns are populated from this, so the user can never pick an empty month.
- `/log/progress` — spec view two.

### Aggregation per exercise per month

`best_weight` (max, null for bodyweight), `avg_reps`, `avg_weight` (null for
bodyweight), plus `set_count` and `session_count` for context. An exercise
appears if it has sets in *either* month; the missing side is null.

**Custom workouts are excluded** (`training_day_id IS NOT NULL`) — they are
improvised around missing equipment, so their numbers would distort the trend.
They still appear in `/log/workouts`, labelled "Custom".

**Aggregate in Python, not in SQL.** `date_trunc` and `AT TIME ZONE` are
Postgres-specific, and the test suite runs on in-memory SQLite. One user's
training history is small enough that pulling the sets and bucketing them in the
service costs nothing and keeps the tests dialect-free.

**Timezone matters here.** `workout.date` is `timestamptz`, so bucketing into
calendar months needs a fixed zone — otherwise a Sunday-evening session lands in
the wrong month depending on where it is read. Implemented as `settings.TIMEZONE`
(`Europe/Berlin`) with `local_month`/`month_key` in `app/core/time.py`, and
covered by a test: 2026-03-31 22:30 UTC is already April in Berlin and must
report as `2026-04`.

Also excluded: sessions with `attended=False`. A cancelled session should carry
no sets, but the filter protects the average against ones entered after the fact.

Weights are `Numeric`, so they arrive as `Decimal` and Pydantic serialises them
as JSON strings. The frontend must parse rather than assume numbers.

`ProgressComparison` also returns `excluded_custom_workouts`, so the log can
explain why a session visible in the history is missing from the analysis.

Verified against the seeded database: Seed Ben's Bankdrücken compares
**11/2025 → 07/2026 as 62.50 → 80.00 kg (+17.50)** across a plan change — the
case that returned nothing before phase 1.

---

## Phase 3 — Frontend scaffold ✅ done

Vite 8 + React 19 + TypeScript + Tailwind v4 under `frontend/`, dark and
minimal per the spec. `npm run build`, `npm run typecheck` and `npm run lint`
are all clean.

```
frontend/src/
├── api/
│   ├── schema.d.ts       generated — do not edit by hand
│   ├── client.ts         openapi-fetch client + unwrap()
│   ├── queries.ts        one queryOptions per endpoint the app reads
│   └── types.ts          short names for the generated schemas
├── components/           AppShell, Placeholder, ui.tsx primitives
├── lib/                  queryClient, useUserId
├── pages/                ProfilePicker, MainMenu, NotFound, placeholders
├── routes.tsx            the navigation below
├── index.css             Tailwind + design tokens
└── main.tsx
```

- **Typed client.** `src/api/schema.d.ts` is generated from the backend's own
  OpenAPI document; `npm run gen:api` regenerates it against a running server.
  A renamed field is now a compile error, not a runtime `undefined`.
- **`unwrap()`** turns openapi-fetch's `{ data } | { error }` result into a
  rejected promise, because TanStack Query needs a rejection to mark a query
  as failed. FastAPI's `detail` — string or 422 list — becomes the message of
  an `ApiError` carrying the status code.
- **TanStack Query** with `refetchOnWindowFocus: false` (single local user, no
  concurrent writers) and no retry below status 500 — a 404 will not become
  correct by asking again.
- **Design tokens** live in a Tailwind v4 `@theme` block in `index.css`:
  surfaces, content, accent, feedback. Components use `bg-surface-raised`,
  never a hex value, so the palette has one source of truth.
- **Routing by id** (`/u/:userId`), with `useUserId()` throwing on a
  non-numeric segment so it lands on the error element instead of firing a
  request for `/api/v1/users/NaN`.
- Mobile first: 44px minimum tap targets, `env(safe-area-inset-*)` padding,
  `overscroll-behavior-y: none`, and `.tabular` so set numbers line up.

Two things worth knowing:

- **TypeScript is pinned to `~5.9`.** The Vite template ships TS 6, but
  `openapi-typescript@7.13` still declares `peer typescript@^5.x`, so the
  install fails on it. Pinning is reproducible; `--legacy-peer-deps` would
  only have hidden the conflict until the next `npm install`.
- **`BACKEND_CORS_ORIGINS` already contained `http://localhost:5173`**, so
  nothing had to change on the backend. Verified with a preflight:
  `access-control-allow-origin: http://localhost:5173`.

`VITE_API_BASE_URL` (see `frontend/.env.example`) points at the backend and
defaults to `http://127.0.0.1:8000`.

Running it:

```bash
cd backend  && uv run uvicorn app.main:app --reload
cd frontend && npm run dev          # http://localhost:5173
```

**Left for phase 4:** every screen except the profile picker and the main menu
is a `Placeholder`. The routes exist so the navigation can be walked end to
end.

---

## Phase 4 — Screens ✅ done

Scope fixed on 2026-09-02 from the "Updates post phase 3" section of
`trainingstracker_specs.md`.

```
/                     profile picker
/:user                main menu
/:user/plans          plan list + create + duplicate + switch the active plan
/:user/plans/:id      plan editor (catalog picker, ordering)
/:user/exercises      exercise catalog
/:user/workout        day picker (Day 1 — Push … | Custom)
/:user/workout/:id    live workout: timer, exercise list, set entry
/:user/log            history
/:user/log/progress   month vs month comparison
/:user/settings       edit user data
```

`/:user/active-plan` is gone: one choice among the plans does not deserve a
menu row of its own, so switching becomes a control in the plan list.

### 4.0 Backend prerequisites ✅ done

Revision `92d47e8a52d8`, 63 tests green (15 new). Three changes had to land
before the screens could be built.

**`workout.body_weight`, Numeric(5,2), nullable.** The log shows the body
weight of the day, and `appuser.weight` is a single scalar that `PATCH`
overwrites — reading it per row would print today's weight next to a session
from March and look like history. The value is therefore snapshotted into the
workout when it is created, copied from `appuser.weight`; **the user never
types it**. Editing the weight in the settings screen changes what future
workouts record and leaves past ones untouched. Nullable because the seeded
and pre-existing rows have no honest value to backfill.

This also makes bodyweight progress readable: 10 pull-ups at 83 kg and 10 at
78 kg are not the same achievement, so the progress view can show body weight
per month next to the reps.

**`POST /api/v1/workouts/sync`** — one workout with its sets nested, written in
one transaction. Needed for the offline draft (§4.4). The body carries a
client-generated `client_uuid` with a unique constraint: when the server
commits but the response is lost on gym wifi, the retry must not duplicate the
whole session. `started_at`/`finished_at` come from the payload rather than
from server-now, or a session synced the next morning records as twelve hours
long.

**`POST /api/v1/workout-plans/{id}/duplicate`** — copies the plan with its
training days and `training_day_exercise` rows, but no workouts. A new plan is
almost always the previous one with two exercises swapped. Copying references
to the catalog (never the exercises themselves) is what keeps the progress
comparison working across the copy. The date range is not copied either: a
fresh copy has not started, and the old plan's dates would simply be wrong.
The title defaults to `"<title> (Copy)"` and can be overridden in the body.

As built, two details differ from the sketch above. The unique constraint on
`client_uuid` is **named** (`workout_client_uuid_einmalig`) — autogenerate
emitted it unnamed again, which would have left `downgrade` unable to drop it,
the same defect as in `ca67bbcf8314`. And `seed.py` now writes a body-weight
drift across the seeded history (two kilos down over six months to today's
profile weight), because a snapshot taken retroactively would otherwise print
the same number against every session and make the column look pointless.

### 4.1 Main menu ✅ done

Rows: start a workout, workout plans, exercise catalog, training log, edit
user data. Above them, two panels:

- **Next up.** The active plan, plus which training day is due — derived from
  the most recent attended workout's `training_day.position`, cycling to the
  next. A panel that only prints the plan title is decoration; naming the next
  day answers the question you opened the app with, and the day picker
  preselects it.
- **Last session.** Date, days since, what it was. One `/log/workouts?limit=1`.

**Resume, if a workout is running.** `started_at` set and `finished_at` null
means the session is still open — you closed the tab or your phone locked.
Without this the menu only offers "start", so you would create a second
workout while the first stays open until `auto_close_stale` writes a phantom
six-hour session into your history. When one is running the menu leads with
"Resume — Push, running 24 min" and demotes "start" below it.

### 4.2 Marking a session missed ✅ done

`attended=False` exists in the model and the log already renders it, but
nothing can create one. A plan has training days and no dates, so nothing
knows you *meant* to train on Tuesday — marking a session missed means writing
a workout row retroactively, with no times and no sets.

Two entry points, and deliberately no form:

- On the day picker, the row's main tap starts the session; a secondary
  control marks it missed for today in one tap. It writes optimistically and
  offers a five-second undo toast instead of a confirmation dialog — a missed
  session is trivially reversible, so confirming costs more than the mistake.
- In the log, "log a missed session" backfills a past date, because you
  remember on Thursday that you skipped Tuesday.

### 4.3 Exercise catalog ✅ done

`exercise` is already generic — `title`, `weighted`, `user_id`, nothing else.
Target sets and rep ranges belong to `training_day_exercise`, actual weights to
`exercise_set`. **The catalog screen must keep it that way:** it edits the name
and the weighted flag, and nothing about sets, reps or weight.

It exists because of `UNIQUE(user_id, title)`. Type "Bankdrucken" once in a
custom workout and you own a second catalog row that splits that exercise's
history in two — the exact failure phase 1 removed. Renaming and deleting are
the repair tools, and this is the only data the app can currently create but
never fix.

### 4.4 Live workout, and offline ✅ done

The screen that has to work one-handed on a phone mid-set: large tap targets,
numeric keypads, the target (3×8-10) visible, last session's numbers
prefilled.

**A rep range is a target, not a rule.** Six reps against an 8-10 target is
recorded silently — no miss marker, no warning.

**Sets are written to local storage as they happen, and synced as one whole
workout on finish** (`POST /workouts/sync`). The alternative — `POST /workouts`
for an id, then one `POST /sets` per set — cannot work offline: the queued sets
reference an id the server has not issued yet, so every replay has to rewrite
ids and preserve ordering across two resources. Making the workout the unit of
sync turns offline into "the request has not gone out yet".

Only completed workouts sync; a running one arriving late could be picked up by
`auto_close_stale`. The side effect is worth as much as the offline support:
your sets survive a crashed tab or a dead battery, because they were never
only in memory.

### 4.5 Colour ✅ done

Purple accent (`--color-accent`), dark and restrained, per the spec update.

**Colour carries only two meanings: error and improvement.** A falling number
in the progress table is not coloured red — it reads as a sign and a down
arrow, with green reserved as the only coloured delta. Otherwise "you lost
5 kg on bench" and a primary button would signal the same thing, and red would
mean both "worse" and "wrong".

---

### 4.6 As built

- **Storage is `localStorage`, not IndexedDB.** A session is a few kilobytes,
  and a synchronous read keeps the live screen free of loading states. The
  reasons for keeping the draft local at all are unchanged.
- **One live route, `/workout/live`,** not one per workout id: the session has
  no server id until it is finished and synced, so there is nothing to put in
  the URL. Resuming means finding the draft on the device, which also survives
  a closed tab, a locked phone and a dead battery.
- **"Next up"** is the training day after the most recent *attended, non-custom*
  session, cycling round. Custom sessions are skipped because they are
  improvised and say nothing about where you are in the rotation.
- **Set rows are prefilled to `target_sets`** — three empty rows for a 3×8-10 —
  so the usual case is typing numbers rather than tapping "add" first. Rows
  left empty are not saved.
- **The catalog cannot express sets or reps,** by construction: the form edits
  a name and the weighted flag, nothing else.

---

## Phase 5 — PWA ✅ done

Installable on the iPhone, served over real HTTPS from the tailnet.

### 5.1 One origin, because HTTPS forces it

A service worker only registers on HTTPS or `localhost` — no exceptions on
iOS. And an HTTPS page may not call an HTTP API (mixed content). Serving the
app from `http://192.168.178.29:5173` would therefore have failed twice over:
no service worker, no install, and no way to reach the API once it was secure.

So **the backend serves the built frontend**. `app/main.py` mounts
`frontend/dist` at `/`, the API keeps `/api/v1`, and everything lives on one
origin. CORS stops mattering entirely; it stays configured only for the dev
server on 5173.

Two details that were not obvious:

- **`StaticFiles(html=True)` is not an SPA fallback.** It only falls back for
  directory paths, so `/u/3/log/progress` returned 404 on reload. `SpaStaticFiles`
  catches the 404 and serves `index.html` — and it has to *catch* it, because
  `StaticFiles` raises the 404 rather than returning it.
- **That fallback must exclude `/api/`.** Without the guard an API typo
  answered with the HTML shell and status 200, so a client expecting JSON got
  "success" and a web page.
- **`/sw.js` is served with `Cache-Control: no-cache`.** A cached service
  worker is one that can never ship an update again.

### 5.2 Caching

`vite-plugin-pwa`, `registerType: 'autoUpdate'`. Precaches the built shell
(15 entries, ~395 KiB) so the app opens with no connection.

API **reads** are cached NetworkFirst with a 5s timeout: online you always get
fresh data, offline you get the last thing you saw, which is enough to run a
workout from your plan. **Writes are not cached and not queued** — they fail
honestly. The one write that must survive offline, logging sets, was already
solved in §4.4 by the local draft and the one-shot sync on finish.

Auto-update is safe here specifically *because* the draft lives in
`localStorage` and survives the reload. An in-memory workout screen would make
`autoUpdate` a data-loss bug.

### 5.3 Install and launch

- Icons generated at 192, 512, a maskable 512 (mark inside the middle 80%, since
  Android crops to its own shape) and a square 180 for iOS, which applies its
  own rounding.
- iOS offers no install prompt and never will — it is Share → Add to Home
  Screen, in Safari only.
- **The installed app opens straight into the profile you used last**
  (`lib/lastProfile.ts`). `start_url` is `/`, which would otherwise mean the
  profile picker on every single launch. Only in standalone mode: in a browser
  tab the picker is a page you navigated to deliberately. "Switch profile"
  clears the memory first, or the app would bounce right back in.

### 5.4 Hosting: Tailscale

`tailscale serve --bg 8000` proxies the tailnet hostname to the local backend
with a genuine Let's Encrypt certificate — verified end to end, `curl` with no
`-k`, subject `CN=macbook-air-von-daniel.tailaf0ce9.ts.net`. Nothing is exposed
to the public internet, which matters because the API still has no
authentication: anyone who can reach it can read and delete every profile.

Running it:

```bash
cd frontend && npm run build      # after any frontend change
cd backend  && uv run uvicorn app.main:app --port 8000
tailscale serve --bg 8000         # once; persists until `--https=443 off`
```

---

## Open questions

None open.

Answered on 2026-09-02:

- Routing goes **by id** (`/u/3`) with the name only displayed, since
  `appuser.name` is not unique.
- Bodyweight progress shows **both** average reps and best-set reps.
- **A rep range is a target, not a rule.** Logging 6 reps against an 8-10
  target is recorded silently — no miss marker, no warning. The number stands
  on its own; the progress view is what says whether things are moving.
