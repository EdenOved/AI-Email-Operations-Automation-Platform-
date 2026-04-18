# Architecture (Clean v1)

## 1) What this product is

`email_ops_clean` is a bounded AI email automation product.

It ingests inbound email, stores it, classifies/extracts structured intent with AI, routes actions to CRM/Jira/HITL/no-action, executes integrations, and gives operators clear visibility for cases, approvals, operations, and eval quality.

It is intentionally **not** a general agent platform, chatbot framework, or multi-agent system.

---

## 2) End-to-end flow

1. **Gmail sync** polls message IDs and fetches message payloads.
2. **Ingest** normalizes Gmail data and persists new emails (with dedup + time gates).
3. **Process** runs LLM classify/extract, applies bounded routing policy + confidence/HITL policy.
4. **Thread policy** decides create/update/comment foundations for CRM/Jira follow-ups.
5. **Routing outcomes**:
   - `noop` -> mark processed
   - `hitl` -> create approval request
   - `crm_only | jira_only | both` -> create integration jobs
6. **Integrations execution** runs planned jobs, stores attempts, updates final email status.
7. **Operator UI** reads projections for:
   - cases inbox
   - case detail debugger
   - approvals queue
   - operations metrics
   - eval dataset/runs/results
8. **Evals** run golden dataset (builtin + HITL-promoted cases) through the same routing logic.

---

## 3) Backend module responsibilities

- `app/core/*`
  - settings and logging bootstrap.
- `app/db/*`
  - SQLAlchemy session/models and small focused repo helpers.
- `app/ingest/*`
  - Gmail API client, normalization, ingest persistence logic.
- `app/sync/service.py`
  - polling loop cycle logic, checkpoint/baseline/reset behavior.
- `app/process/*`
  - LLM classify/extract, routing policy, thread-aware planning, HITL decision entry.
- `app/integrations/*`
  - HubSpot/Jira provider clients and integration execution orchestration.
- `app/hitl/service.py`
  - approval transitions (approve/reject), post-approval resume, HITL->golden promotion.
- `app/evals/*`
  - dataset construction, judge utility, eval run service.
- `app/operator/queries.py`
  - read-model/projection queries for inbox/detail/ops surfaces.
- `app/api/routes/*`
  - HTTP surfaces split by product area (`health`, `cases`, `approvals`, `operations`, `evals`, `webhooks`).
- `app/runners/gmail_sync.py`
  - sync runner entrypoint for background polling process.

---

## Prompt system boundaries

- Process prompt files:
  - `backend/app/process/prompts/classify_extract/system.txt`
  - `backend/app/process/prompts/classify_extract/user.txt`
- Eval judge prompt files:
  - `backend/app/evals/prompts/judge/system.txt`
  - `backend/app/evals/prompts/judge/user.txt`

Prompt-driven responsibilities:
- Model instructions for classify+extract output shape and quality.
- User-input rendering for email subject/body passed to classify+extract.
- Eval-judge scoring guidance and case rendering for offline eval runs.

Code-driven responsibilities (intentional):
- Routing mapping (`route_from_classification`) and confidence HITL policy.
- Thread policy and integration action planning.
- Approval/HITL state transitions and resume flow.
- Integration execution status handling.
- Ingest/sync behavior, checkpointing, dedup, and persistence.

This keeps prompt content editable without moving deterministic business policy into prompt text.

---

## 4) Frontend area responsibilities

- `src/app/*`
  - route shells only (thin pages).
- `src/features/cases/*`
  - cases inbox + case detail behavior (data fetching + rendering).
- `src/features/approvals/*`
  - HITL approvals queue + decision actions.
- `src/features/operations/*`
  - operations dashboard metrics and integration health view.
- `src/features/evals/*`
  - eval dataset/runs/results interactions.
- `src/lib/*`
  - API helper + formatting helpers.
- `src/types/*`
  - typed UI contracts.
- `src/components/*`
  - minimal shared UI primitives.

---

## 5) Main runtime paths

- **API server**: `app.main`
  - Run with `uvicorn app.main:app --reload --port 8001`
- **Gmail sync runner**: `app.runners.gmail_sync`
  - Run with `python -m app.runners.gmail_sync --tenant-slug demo`

Together they form the primary local runtime.

---

## 6) Intentionally deferred in clean v1

- full Gmail `users.history` parity complexity
- advanced provider retry taxonomy and deep reliability matrix
- advanced thread heuristics beyond clean create/update/comment foundations
- distributed bus workers / multi-process orchestration
- non-essential framework abstractions

The goal is a compact, readable, stable baseline that preserves core product behavior with minimal accidental complexity.
