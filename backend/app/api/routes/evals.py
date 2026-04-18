from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvalRun, EvalRunCaseResult
from app.db.session import get_session
from app.evals.dataset import build_eval_dataset
from app.evals.service import run_eval
from app.hitl.service import promote_hitl_to_golden
from app.schemas.approvals import PromoteHitlPayload
from app.schemas.evals import EvalRunCreatePayload

router = APIRouter(prefix="/api/v1/operator", tags=["evals"])


@router.get("/evals/dataset")
async def evals_dataset(session: AsyncSession = Depends(get_session)) -> dict:
    return {"items": await build_eval_dataset(session)}


@router.post("/evals/runs")
async def evals_run_create(payload: EvalRunCreatePayload, session: AsyncSession = Depends(get_session)) -> dict:
    run = await run_eval(session, judge_enabled=payload.judge_enabled)
    return {"run_id": run.id}


@router.get("/evals/runs")
async def evals_runs(session: AsyncSession = Depends(get_session), limit: int = Query(default=30, ge=1, le=200)) -> dict:
    q = await session.execute(EvalRun.__table__.select().order_by(EvalRun.created_at.desc()).limit(limit))
    return {"items": [dict(row._mapping) for row in q.fetchall()]}


@router.get("/evals/runs/{run_id}")
async def evals_run_detail(run_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    cases = await session.execute(EvalRunCaseResult.__table__.select().where(EvalRunCaseResult.run_id == run_id))
    return {
        "run": {
            "id": run.id,
            "status": run.status,
            "model": run.model,
            "judge_model": run.judge_model,
            "pass_rate": run.pass_rate,
            "case_total": run.case_total,
            "route_pass": run.route_pass,
            "route_fail": run.route_fail,
            "judge_avg_overall": run.judge_avg_overall,
            "created_at": run.created_at.isoformat(),
        },
        "cases": [dict(row._mapping) for row in cases.fetchall()],
    }


@router.post("/evals/golden/from-hitl")
async def evals_promote_hitl(payload: PromoteHitlPayload, session: AsyncSession = Depends(get_session)) -> dict:
    if not payload.email_id:
        raise HTTPException(status_code=400, detail="email_id required")
    try:
        return await promote_hitl_to_golden(session, payload.email_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
