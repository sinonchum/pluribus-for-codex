# Pluribus Backend

FastAPI and SQLite foundation for the Pluribus mission coordinator.

## Requirements

- Python 3.11
- `uv`
- Git CLI

## Setup and verification

```bash
cd backend
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

## Run locally

```bash
cd backend
PLURIBUS_DB_PATH=.pluribus/pluribus.db \
  uv run uvicorn app.main:app --reload --port 8000
```

Useful endpoints:

- OpenAPI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>
- Create mission: `POST /api/missions`
- Mission events: `GET /api/missions/{id}/events`

The start endpoint calls the injected `MissionController` protocol. Until the
orchestration workstream connects an implementation, it returns a typed `503`
instead of pretending that a mission started.
