# Email-Operations-Automation-Platform

`Gmail sync -> store -> LLM classify/extract -> bounded routing -> HITL when needed -> HubSpot/Jira execution -> operator UI -> evals/ops`

## Why this repo exists

This project keeps the real product behavior while removing accidental complexity:

- one backend
- one frontend
- one operator UI system
- one main ingest/sync path
- one main routing/integration pipeline
- no legacy UI fallback
- no bus/distributed complexity in v1

## Backend module map (compact, non-god-file)

- `app/core/*` - settings + logging
- `app/db/*` - session, models, targeted repos
- `app/ingest/*` - Gmail client + normalize + ingest service
- `app/sync/service.py` - checkpoint/baseline/reset-aware poll cycle
- `app/process/*` - LLM classify/extract + routing + thread-aware planning
- `app/integrations/*` - provider clients + execution service
- `app/hitl/service.py` - approvals decisioning + HITL->golden promotion
- `app/evals/*` - dataset, judge, eval run service
- `app/operator/queries.py` - operator projections for inbox/detail/ops
- `app/api/routes/*` - health/cases/approvals/operations/evals/webhooks
- `app/runners/gmail_sync.py` - sync loop entrypoint

## Prompt system (final layout)

- Process prompts (main classify+extract task):
  - `backend/app/process/prompts/classify_extract/system.txt`
  - `backend/app/process/prompts/classify_extract/user.txt`
- Eval judge prompts (eval-only scoring task):
  - `backend/app/evals/prompts/judge/system.txt`
  - `backend/app/evals/prompts/judge/user.txt`

Prompt-driven parts:
- LLM classify+extract instructions and email input rendering
- Eval judge instructions and eval-case rendering

Code-driven parts (intentionally not in prompts):
- routing policy and confidence thresholds
- HITL gating and approval transitions
- thread-aware action planning (create/update/comment)
- integration execution/retry behavior
- sync/ingest mechanics and data persistence

## Structure

```text
email_ops_clean/
  .env.example
  docker-compose.yml
  backend/
    app/
    migrations/
    scripts/reset_local.ps1
    pyproject.toml
    alembic.ini
  frontend/
    src/app/...
```

## Local run

1. Start Postgres:

```powershell
docker compose up -d
```

2. Create env:

```powershell
Copy-Item .env.example .env
Copy-Item .env.example backend/.env
```

3. Backend install + migrations:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .\backend
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

4. Run backend API:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

5. Run Gmail sync loop (new terminal):

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.runners.gmail_sync --tenant-slug demo
```

6. Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:

- UI: `http://localhost:3001/ops/cases`
- API: `http://127.0.0.1:8001/docs`

7. Run tests:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests -q
```

## Canonical reset

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\reset_local.ps1
```

This script:

- ensures Postgres is up
- runs migrations
- truncates product data tables
- keeps schema intact

## Product surfaces

- Cases inbox
- Case detail (decision quality + integration attempts + retry)
- Approvals (HITL)
- Operations (health/business value/integration reliability)
- Evals (dataset/runs/results + optional judge)

