# Patient Encounter Portal PoC

A proof-of-concept portal for home-health clinicians to manage patient encounters. Built as a monorepo with a **FastAPI** backend and a **React** frontend.

## What It Does

- **Edit simple patient data** -- name and basic demographics
- **Edit the patient's Medical History** -- freeform text stored per patient
- **Edit Encounter Transcripts** -- multiple dated transcripts per patient, each attributed to the clinician who wrote it
- **Prevent users from overriding each other's data** -- role-based access control, authorship rules, and a recency lock that restricts non-admin edits to the most recent transcript
- **Generate AI summaries on save** -- when a clinician saves edits, an Anthropic Claude call produces a structured clinical summary they can review in the time it takes to walk from someone's driveway to their front door
- **Minimize costly recomputation** -- summaries are cached in Postgres, only regenerated when content actually changes, skipped when there is nothing to summarize, and silently disabled when no API key is configured. Celery offloads generation to a background worker so saves stay fast

## Quick Start

1. Copy `.env.example` to `.env` and configure `SECRET_KEY` and `ANTHROPIC_API_KEY` at minimum:

   ```bash
   cp .env.example .env
   # edit .env -- set SECRET_KEY and ANTHROPIC_API_KEY
   ```

2. Install dependencies and start the stack:

   ```bash
   uv sync
   bun install
   bun run dev
   docker compose watch
   ```

## Accessing the Services

Credentials are configured in `.env` (see [`.env.example`](.env.example) for defaults).

| Service | URL |
|---------|-----|
| Frontend | <http://dashboard.localhost> |
| Backend API | <http://api.localhost> |
| API docs (Swagger) | <http://api.localhost/docs> |
| Adminer (DB UI) | <http://localhost:8080/?pgsql=db&username=postgres&db=app&ns=public> |
| Traefik dashboard | <http://localhost:8090> |
| Flower (Celery queue) | <http://localhost:5555> |
| Frontend direct (bypassing Traefik) | <http://localhost:5173> |
| Backend direct (bypassing Traefik) | <http://localhost:8000> |

## Running Tests

```bash
# End-to-end (Playwright)
docker compose run --rm playwright bunx playwright test

# Backend unit tests
docker compose exec backend bash scripts/tests-start.sh
```

## Configuration

All configuration is done through environment variables. See [`.env.example`](.env.example) for the full list with descriptions. At minimum you need to set:

- `SECRET_KEY` -- used for JWT signing
- `ANTHROPIC_API_KEY` -- enables AI summary generation (optional; the app works without it)

## Architecture

```
patient-encounter-portal-poc/
├── backend/          Python 3.10+ / FastAPI / SQLModel / Alembic
│   └── app/
│       ├── models.py                 Data models (DB tables + API schemas)
│       ├── api/routes/items.py       Patient CRUD endpoints
│       ├── api/routes/transcripts.py Encounter transcript endpoints
│       ├── core/ai_summary.py        AI summary generation (Anthropic)
│       └── core/celery_app.py        Celery worker / task definitions
│
├── frontend/         React / Vite / TanStack Router + Query
│   └── src/
│       ├── routes/_layout/items_.$id.tsx               Patient detail page
│       ├── components/Items/EditItem.tsx                Edit patient dialog
│       └── components/Items/EncounterTranscripts.tsx    Transcript CRUD UI
│
└── compose.yml       Docker Compose (Postgres, Redis, backend, frontend, Traefik, Celery)
```

The frontend talks to the backend through a **generated OpenAPI client** (`frontend/src/client/sdk.gen.ts`), keeping the two sides in sync automatically.

## Technology Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com), [SQLModel](https://sqlmodel.tiangolo.com), [PostgreSQL](https://www.postgresql.org), [Celery](https://docs.celeryq.dev) + Redis, [Anthropic Claude](https://docs.anthropic.com)
- **Frontend**: [React](https://react.dev), [Vite](https://vitejs.dev), [TypeScript](https://www.typescriptlang.org), [Tailwind CSS](https://tailwindcss.com) + [shadcn/ui](https://ui.shadcn.com), [TanStack Router & Query](https://tanstack.com)
- **Infrastructure**: [Docker Compose](https://docs.docker.com/compose/), [Traefik](https://traefik.io), [Playwright](https://playwright.dev) for E2E tests, [Pytest](https://pytest.org) for backend tests

## Key Files

| Feature | Backend | Frontend |
|---------|---------|----------|
| Data models | `backend/app/models.py` | `frontend/src/client/types.gen.ts` |
| Patient CRUD | `backend/app/api/routes/items.py` | `frontend/src/components/Items/EditItem.tsx` |
| Transcript CRUD | `backend/app/api/routes/transcripts.py` | `frontend/src/components/Items/EncounterTranscripts.tsx` |
| AI summaries | `backend/app/core/ai_summary.py` | `frontend/src/routes/_layout/items_.$id.tsx` |
| Celery tasks | `backend/app/core/celery_app.py` | -- |
| Auth / deps | `backend/app/api/deps.py` | `frontend/src/hooks/useAuth.ts` |
| DB migrations | `backend/app/alembic/versions/` | -- |
| Generated client | -- | `frontend/src/client/sdk.gen.ts` |
