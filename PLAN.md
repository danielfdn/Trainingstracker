# Build plan — from the current backend to the finished PWA

Companion to `trainingstracker_specs.md`. `UMBAU.md` describes how the backend
got to its current state; this file describes where it goes next.

Written in English because that is the language we work in now. The existing
German files (`UMBAU.md`, the code comments under `backend/app/`) stay German.

**Status (2026-09-02):** Phases 0 to 3 done. 48 tests green, 41 endpoints,
Postgres migrated to head (`ca67bbcf8314`), seed data rebuilt. The frontend
scaffold builds, talks to the API and renders the profile picker; the
remaining screens are placeholders.

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

## Phase 4 — Screens

Following the navigation in the spec:

```
/                     profile picker
/:user                main menu
/:user/plans          plan list + create
/:user/plans/:id      plan editor (catalog picker, ordering)
/:user/active-plan    select the active plan
/:user/workout        day picker (Day 1 — Push … | Custom)
/:user/workout/:id    live workout: timer, exercise list, set entry
/:user/log            history
/:user/log/progress   month vs month comparison
/:user/settings       edit user data
```

Starting a workout first asks which training day is up today, listing the active
plan's days by position and type, with "Custom" below the divider. Choosing a day
prefills the screen from `training_day_exercise`; choosing Custom opens the free
exercise picker instead.

The live workout screen is the one that has to work well one-handed on a phone
mid-set: large tap targets, numeric keypads, the target (3×8-10) visible, and
last session's numbers prefilled as the starting point.

---

## Phase 5 — PWA

`vite-plugin-pwa` for manifest and service worker, icons, iOS install metadata,
verified as an installed app on the iPhone.

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
