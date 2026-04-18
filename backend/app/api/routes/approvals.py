from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.hitl.service import decide_approval
from app.operator.queries import pending_approvals
from app.schemas.operator import ApprovalDecisionPayload

router = APIRouter(prefix="/api/v1/operator", tags=["approvals"])


def _require_internal(key: str | None) -> None:
    if get_settings().internal_api_key and key != get_settings().internal_api_key:
        raise HTTPException(status_code=401, detail="invalid internal key")


@router.get("/approvals/pending")
async def approvals_pending(session: AsyncSession = Depends(get_session), limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {"items": await pending_approvals(session, limit=limit)}


@router.post("/approvals/{approval_id}/decide")
async def approvals_decide(
    approval_id: str,
    payload: ApprovalDecisionPayload,
    session: AsyncSession = Depends(get_session),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
) -> dict:
    _require_internal(x_internal_key)
    action = str(payload.action).lower()
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve|reject")
    await decide_approval(
        session,
        approval_id=approval_id,
        action=action,
        reviewer=str(payload.reviewer or "operator"),
        notes=payload.notes,
        override_route=payload.override_route,
    )
    return {"status": "ok"}
