# Backend (clean v1)

Single FastAPI service for bounded email automation:

- Gmail sync ingest
- LLM classify/extract
- bounded routing (`crm_only|jira_only|both|noop|hitl`)
- HITL approvals
- HubSpot/Jira execution
- operator/eval/operations APIs

## Entry points

- API: `uvicorn app.main:app --reload --port 8001`
- Sync loop: `python -m app.runners.gmail_sync --tenant-slug demo`

## Migrations

```powershell
alembic upgrade head
```

## Canonical reset

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_local.ps1
```

## Tests

```powershell
python -m pytest tests -q
```
