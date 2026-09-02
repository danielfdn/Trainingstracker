# Build plan — from the current backend to the finished PWA

Companion to `trainingstracker_specs.md`. `UMBAU.md` describes how the backend
got to its current state; this file describes where it goes next.

Written in English because that is the language we work in now. The existing
German files (`UMBAU.md`, the code comments under `backend/app/`) stay German.

**Starting point (2026-09-02):** 27 tests green, 28 endpoints, Postgres migrated
to head (`418fec70b608`), no frontend.

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

---

## Phase 0 — Commit what exists

`pyproject.toml` and `uv.lock` are still untracked, so a fresh clone cannot
install the project. Also still open from the last cleanup pass: `.DS_Store` and
`__pycache__/main.cpython-314.pyc` are committed to git and should be removed
and gitignored.

---

## Phase 1 — Data model

### 1.1 Exercise becomes a per-user catalog

Today `exercise.workout_plan_id` is `NOT NULL`, so an exercise belongs to exactly
one plan. That breaks the progress comparison: "Bankdrücken" in the autumn plan
and "Bankdrücken" in the spring plan are two rows with two ids, and no join
connects them. The comparison would silently return nothing for every exercise.

```
appuser
  ├─ exercise            (catalog, UNIQUE(user_id, title))
  └─ workout_plan ──< plan_exercise >── exercise
                                          ▲
     workout ──< exercise_set >───────────┘
```

- `exercise`: drop `workout_plan_id`, add `user_id` FK → `appuser` (CASCADE),
  `UNIQUE(user_id, title)`.
- `plan_exercise`: `(workout_plan_id, exercise_id)` composite PK, plus a
  `position` integer so a plan keeps its exercise order.
- `exercise_set` is unchanged — it already points at both `exercise_id` and
  `workout_id`, which is exactly what the aggregation needs.

### 1.2 Exactly one active plan

`appuser.active_workout_plan_id`, nullable, FK → `workout_plan`, `ON DELETE SET NULL`.

A nullable FK makes "at most one" a structural guarantee. An `is_active` boolean
on the plan would allow two rows to be true at once and would need application
code or a partial unique index to prevent it.

This creates a circular FK between `appuser` and `workout_plan`. Alembic needs
`use_alter=True` on the constraint so it emits the `ALTER TABLE` after both
tables exist instead of deadlocking on creation order.

### 1.3 Migration and seed

One Alembic revision covering both changes, then extend `backend/scripts/seed.py`
so it produces a catalog, a plan referencing it, an active plan, and enough
workouts across several months to exercise the comparison view.

---

## Phase 2 — Training log (the first service-layer code)

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

**Aggregate in Python, not in SQL.** `date_trunc` and `AT TIME ZONE` are
Postgres-specific, and the test suite runs on in-memory SQLite. One user's
training history is small enough that pulling the sets and bucketing them in the
service costs nothing and keeps the tests dialect-free.

**Timezone matters here.** `workout.date` is `timestamptz`, so bucketing into
calendar months needs a fixed zone — otherwise a Sunday-evening session lands in
the wrong month depending on where it is read. Assumption: `Europe/Berlin`, as a
setting in `app/core/config.py`.

Weights are `Numeric`, so they arrive as `Decimal` and Pydantic serialises them
as JSON strings. The frontend must parse rather than assume numbers.

---

## Phase 3 — Frontend scaffold

Vite + React + TypeScript + Tailwind, dark and minimal, per the spec.

- Generate a typed client from `/api/v1/openapi.json` (`openapi-typescript` +
  `openapi-fetch`). Backend changes then become frontend compile errors instead
  of runtime surprises.
- TanStack Query for server state — caching, refetching, and optimistic set
  entry during a live workout.
- React Router.
- Design tokens as CSS custom properties so dark stays one source of truth.
- Add the Vite dev origin (`http://localhost:5173`) to `BACKEND_CORS_ORIGINS`.

---

## Phase 4 — Screens

Following the navigation in the spec:

```
/                     profile picker
/:user                main menu
/:user/plans          plan list + create
/:user/plans/:id      plan editor (catalog picker, ordering)
/:user/active-plan    select the active plan
/:user/workout        live workout: timer, exercise list, set entry
/:user/log            history
/:user/log/progress   month vs month comparison
/:user/settings       edit user data
```

The live workout screen is the one that has to work well one-handed on a phone
mid-set: large tap targets, numeric keypads, last session's numbers prefilled as
the starting point.

---

## Phase 5 — PWA

`vite-plugin-pwa` for manifest and service worker, icons, iOS install metadata,
verified as an installed app on the iPhone.

---

## Open questions

1. **Training days.** `workout_plan.training_days` is an integer, but exercises
   hang off the plan as one flat list. If a 4-day plan means push/pull/legs/arms
   with different exercises per day, the model cannot express that today, and
   starting a workout would need to ask *which day*. Is `training_days` just a
   weekly target count, or a real split that needs modelling?

2. **Existing data during the exercise migration.** Does the database hold
   training data worth keeping? If it is only seed data, the migration can
   recreate the tables. If not, it needs a data migration that derives `user_id`
   from each exercise's plan, deduplicates by title, and rewrites
   `exercise_set.exercise_id` to the surviving rows.

3. **Routing by name.** The spec shows `/tom`, but `appuser.name` has no unique
   constraint, so two users named Tom would collide. Add `UNIQUE(name)`, or route
   by id and merely display the name?

4. **Bodyweight progress.** Pull-ups have no weight, so their only progress
   signal is reps. Is average reps enough, or should best-set reps show too?
