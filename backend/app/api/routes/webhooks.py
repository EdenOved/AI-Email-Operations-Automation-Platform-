from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repos.tenants import get_by_slug
from app.db.session import get_session
from app.ingest.service import ingest_gmail_message
from app.integrations.service import execute_jobs_for_email
from app.process.service import run_pipeline_for_email

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/gmail/message")
async def ingest_gmail_by_id(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    tenant_slug = str(payload.get("tenant_slug") or "demo")
    message_id = payload.get("message_id")
    if not message_id:
        raise HTTPException(status_code=400, detail="message_id required")
    tenant = await get_by_slug(session, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    result = await ingest_gmail_message(session, tenant, message_id, min_internal_ts_ms=None, max_internal_age_seconds=0)
    if result.email is None:
        return {"status": "duplicate_or_skipped"}
    await run_pipeline_for_email(session, result.email)
    if result.email.status in ("routed", "partial_failure", "failed"):
        await execute_jobs_for_email(session, result.email.id)
    return {"status": "ok", "email_id": result.email.id}
