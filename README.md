# Trainingstracker

Workout plans, live set logging and monthly progress — a FastAPI backend with a
React PWA that the backend serves itself in production.

- **Backend:** FastAPI + SQLAlchemy + Alembic on PostgreSQL, managed with `uv`.
- **Frontend:** React 19 + Vite + Tailwind, installable as a PWA.
- **Design decisions and the reasoning behind them:** see `PLAN.md`.

---

## Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | current | Fetches Python 3.13 itself (`.python-version`), no system Python needed. |
| Node.js | ≥ 20.19 (22 LTS recommended) | Vite 8 refuses older versions. Raspberry Pi OS Bookworm ships Node 18 via apt — install 22 from NodeSource or nvm. |
| PostgreSQL | ≥ 14 | Local server; the app does not create the database. |

On a Raspberry Pi (Debian):

```bash
sudo apt install postgresql
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install nodejs
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
git clone https://github.com/danielfdn/Trainingstracker.git
cd Trainingstracker
```

**1. Database.** Create the role and the database the `.env` will point at:

```bash
sudo -u postgres createuser --pwprompt trainingstracker
sudo -u postgres createdb --owner=trainingstracker trainingstracker
```

**2. Environment.** Copy the template and fill in the values from step 1:

```bash
cp .env.example .env
```

`backend/app/core/config.py` reads this file by absolute path, so it works no
matter which directory you start `uvicorn` or `alembic` from. `frontend/.env`
is optional — see `frontend/.env.example`; the defaults are right for both dev
and production.

**3. Dependencies.**

```bash
uv sync                      # backend (installs Python 3.13 if missing)
npm install                  # root dev-runner (concurrently)
npm --prefix frontend install
```

**4. Schema.**

```bash
cd backend && uv run alembic upgrade head && cd ..
```

Optional sample data across several months, so the progress view has something
to compare:

```bash
cd backend && uv run python -m scripts.seed && cd ..
```

## Development

```bash
npm run dev
```

Backend on <http://127.0.0.1:8000> (docs at `/docs`), frontend on
<http://localhost:5173>, talking to it via CORS. Either half alone:
`npm run dev:backend` / `npm run dev:frontend`.

```bash
npm test                     # pytest
npm --prefix frontend run typecheck
npm --prefix frontend run lint
```

After changing an API route, regenerate the typed client against a running
backend: `npm --prefix frontend run gen:api`.

## Production

In production the backend serves the built frontend from the same origin —
that is what makes the PWA installable, since a service worker needs HTTPS and
an HTTPS page may not call an HTTP API.

```bash
npm run build                                    # writes frontend/dist
cd backend && uv run uvicorn app.main:app --port 8000
```

`app/main.py` mounts `frontend/dist` only if it exists, so **rebuild after
every frontend change**. Without the build you get a working API and nothing
else.

### Exposing it over Tailscale

```bash
tailscale serve --bg 8000    # once; persists until `tailscale serve --https=443 off`
```

This gives the tailnet hostname a real Let's Encrypt certificate. Keep
uvicorn bound to `127.0.0.1` — Tailscale proxies to it locally. Do **not**
expose the port to the public internet: the API has no authentication, and
anyone who can reach it can read and delete every profile.

## Upgrading an existing installation

```bash
git pull
uv sync && npm install && npm --prefix frontend install
cd backend && uv run alembic upgrade head && cd ..
npm run build
```

## Layout

```
backend/app/        FastAPI app: api/ routes, entities/, repositories/, schemas/, services/
backend/alembic/    migrations
backend/scripts/    seed.py
backend/tests/      pytest suite
frontend/src/       React app: pages/, components/, api/, lib/
PLAN.md             architecture and design decisions
```
