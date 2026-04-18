from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Email, EmailEvent, IntegrationAttempt, IntegrationJob
from app.integrations.hubspot_client import execute as hubspot_execute
from app.integrations.jira_client import execute as jira_execute
from app.utils import new_id


async def execute_jobs_for_email(session: AsyncSession, email_id: str) -> dict:
    q = await session.execute(
        select(IntegrationJob).where(and_(IntegrationJob.email_id == email_id, IntegrationJob.status.in_(["planned", "failed"])))
    )
    jobs = list(q.scalars().all())
    out = {"succeeded": 0, "failed": 0, "skipped": 0}
    for job in jobs:
        if job.provider == "hubspot":
            status, code, body, external = await hubspot_execute(job.payload_json, job.action)
        else:
            status, code, body, external = await jira_execute(job.payload_json, job.action)
        job.status = status
        job.external_id = external
        job.error_detail = None if status == "succeeded" else body
        session.add(
            IntegrationAttempt(
                id=new_id("att"),
                job_id=job.id,
                status=status,
                response_code=code if code else None,
                response_body=body[:1000] if body else None,
                error_detail=body[:1000] if status != "succeeded" else None,
            )
        )
        out[status] = out.get(status, 0) + 1
    email = await session.get(Email, email_id)
    if email:
        if out.get("failed", 0) > 0:
            email.status = "partial_failure" if out.get("succeeded", 0) > 0 else "failed"
        elif out.get("succeeded", 0) > 0 or out.get("skipped", 0) > 0:
            email.status = "processed"
        session.add(EmailEvent(id=new_id("evt"), email_id=email.id, event_type="integrations_executed", detail_json=out))
    await session.commit()
    return out
