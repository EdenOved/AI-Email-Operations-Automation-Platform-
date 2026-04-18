from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ApprovalRequest, Email, ExtractionRun, GoldenCaseCandidate, HumanReview
from app.integrations.service import execute_jobs_for_email
from app.process.service import plan_integration_jobs
from app.process.thread_policy import build_thread_context
from app.schemas.llm import StructuredResult
from app.utils import new_id


async def decide_approval(
    session: AsyncSession,
    approval_id: str,
    action: str,
    reviewer: str = "operator",
    notes: str | None = None,
    override_route: str | None = None,
) -> None:
    approval = await session.get(ApprovalRequest, approval_id)
    if not approval:
        raise ValueError("approval not found")
    email = await session.get(Email, approval.email_id)
    if not email:
        raise ValueError("email not found")
    session.add(
        HumanReview(
            id=new_id("rev"),
            approval_request_id=approval.id,
            reviewer=reviewer,
            action=action,
            notes=notes,
            override_route=override_route,
        )
    )
    if action == "reject":
        approval.status = "rejected"
        email.status = "rejected"
        await session.commit()
        return
    route = override_route or approval.proposed_route or "crm_only"
    approval.status = "approved"
    dummy = StructuredResult.model_validate((approval.snapshot_json or {}).get("parsed") or {})
    run = ExtractionRun(
        id=new_id("ext"),
        email_id=email.id,
        status="succeeded",
        model=get_settings().openai_model if get_settings().openai_api_key else "heuristic",
        parsed_json=dummy.model_dump(),
        error_detail=None,
    )
    session.add(run)
    await session.commit()
    thread_ctx = await build_thread_context(session, email)
    await plan_integration_jobs(session, email, route, run.id, dummy, thread_ctx)
    await execute_jobs_for_email(session, email.id)


async def promote_hitl_to_golden(session: AsyncSession, email_id: str) -> dict:
    email = await session.get(Email, email_id)
    if not email:
        raise ValueError("email not found")
    approval = (
        await session.execute(select(ApprovalRequest).where(ApprovalRequest.email_id == email_id).order_by(desc(ApprovalRequest.created_at)).limit(1))
    ).scalar_one_or_none()
    if approval is None or approval.status not in ("approved", "rejected"):
        raise ValueError("requires resolved approval")
    reviews = list((await session.execute(select(HumanReview).where(HumanReview.approval_request_id == approval.id))).scalars().all())
    if not reviews:
        raise ValueError("requires human review record")
    expected = approval.proposed_route or "hitl"
    existing = (await session.execute(select(GoldenCaseCandidate).where(GoldenCaseCandidate.email_id == email_id))).scalar_one_or_none()
    if existing:
        existing.expected_route = expected
        existing.expect_hitl = True
    else:
        session.add(
            GoldenCaseCandidate(
                id=new_id("gld"),
                email_id=email_id,
                case_name=(email.subject or "HITL case")[:500],
                subject=email.subject,
                body=email.body_text,
                expected_route=expected,
                expect_hitl=True,
                source_json={"approval_id": approval.id},
            )
        )
    await session.commit()
    return {"status": "ok", "expected_route": expected}
