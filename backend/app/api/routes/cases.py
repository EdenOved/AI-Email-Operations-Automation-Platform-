from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.integrations.service import execute_jobs_for_email
from app.operator.queries import get_case_detail, list_inbox

router = APIRouter(prefix="/api/v1/operator", tags=["cases"])


def _require_internal(key: str | None) -> None:
    if get_settings().internal_api_key and key != get_settings().internal_api_key:
        raise HTTPException(status_code=401, detail="invalid internal key")


@router.get("/inbox")
async def inbox(
    session: AsyncSession = Depends(get_session),
    only_failures: bool = Query(default=False),
    only_approvals: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    return await list_inbox(session, only_failures=only_failures, only_approvals=only_approvals, limit=limit)


@router.get("/cases/{email_id}")
async def case_detail(email_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    data = await get_case_detail(session, email_id)
    if data is None:
        raise HTTPException(status_code=404, detail="email not found")
    return data


@router.post("/cases/{email_id}/retry-integrations")
async def retry_integrations(
    email_id: str,
    session: AsyncSession = Depends(get_session),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
) -> dict:
    _require_internal(x_internal_key)
    return await execute_jobs_for_email(session, email_id)
