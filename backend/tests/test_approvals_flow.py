import pytest
from sqlalchemy import select

from app.db.models import ApprovalRequest, Email, ExtractionRun, HumanReview, Tenant
from app.hitl import service as hitl_service
from app.utils import new_id


def _parsed_snapshot() -> dict:
    return {
        "classification": {
            "primary_intent": "crm_focused",
            "sensitivity": "normal",
            "routing_confidence": 0.9,
            "route_reason_summary": "test",
            "uncertainty_indicators": [],
            "human_review_recommended": False,
            "content_category": "actionable",
        },
        "extraction": {
            "account_name": "Acme",
            "contact_email": "a@acme.com",
            "jira_summary": "Bug",
            "jira_description": "Details",
            "suggested_priority": "medium",
            "suggested_action": "create",
        },
    }


@pytest.mark.asyncio
async def test_reject_approval_sets_email_rejected(db_session):
    tenant = (await db_session.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one()
    email = Email(
        id=new_id("eml"),
        tenant_id=tenant.id,
        provider="gmail",
        provider_message_id="m-approve-reject",
        from_address="a@x.com",
        status="awaiting_approval",
    )
    db_session.add(email)
    approval = ApprovalRequest(
        id=new_id("apr"),
        email_id=email.id,
        status="pending",
        reason="low_confidence",
        proposed_route="crm_only",
        snapshot_json={"parsed": _parsed_snapshot()},
    )
    db_session.add(approval)
    await db_session.commit()

    await hitl_service.decide_approval(db_session, approval.id, "reject", reviewer="t")
    refreshed = await db_session.get(Email, email.id)
    assert refreshed.status == "rejected"
    reviews = list((await db_session.execute(select(HumanReview).where(HumanReview.approval_request_id == approval.id))).scalars().all())
    assert len(reviews) == 1


@pytest.mark.asyncio
async def test_approve_transitions_to_job_planning(db_session, monkeypatch):
    tenant = (await db_session.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one()
    email = Email(
        id=new_id("eml"),
        tenant_id=tenant.id,
        provider="gmail",
        provider_message_id="m-approve-ok",
        from_address="a@x.com",
        status="awaiting_approval",
    )
    db_session.add(email)
    approval = ApprovalRequest(
        id=new_id("apr"),
        email_id=email.id,
        status="pending",
        reason="low_confidence",
        proposed_route="crm_only",
        snapshot_json={"parsed": _parsed_snapshot()},
    )
    db_session.add(approval)
    await db_session.commit()

    async def fake_execute_jobs(session, email_id):
        return {"succeeded": 0, "failed": 0, "skipped": 1}

    monkeypatch.setattr(hitl_service, "execute_jobs_for_email", fake_execute_jobs)

    await hitl_service.decide_approval(db_session, approval.id, "approve", reviewer="t")
    refreshed = await db_session.get(Email, email.id)
    assert refreshed.status in ("routed", "processed", "partial_failure", "failed")
    extraction_runs = list((await db_session.execute(select(ExtractionRun).where(ExtractionRun.email_id == email.id))).scalars().all())
    assert len(extraction_runs) >= 1
