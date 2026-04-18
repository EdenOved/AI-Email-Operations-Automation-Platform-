import pytest
from sqlalchemy import select

from app.db.models import Email, IntegrationAttempt, IntegrationJob, RoutingDecision, Tenant
from app.integrations import service as integration_service
from app.utils import new_id


@pytest.mark.asyncio
async def test_integration_status_partial_failure(db_session, monkeypatch):
    tenant = (await db_session.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one()
    email = Email(
        id=new_id("eml"),
        tenant_id=tenant.id,
        provider="gmail",
        provider_message_id="m-int-1",
        from_address="a@x.com",
        status="routed",
    )
    db_session.add(email)
    decision = RoutingDecision(
        id=new_id("rd"),
        email_id=email.id,
        extraction_run_id=new_id("ext"),
        route="both",
        rationale="test",
        requires_hitl=False,
        decision_confidence=0.9,
        route_reason_summary="test",
        uncertainty_indicators_json=[],
        human_review_recommended=False,
        content_category="actionable",
    )
    db_session.add(decision)
    db_session.add(
        IntegrationJob(
            id=new_id("job"),
            email_id=email.id,
            routing_decision_id=decision.id,
            provider="hubspot",
            action="create",
            status="planned",
            payload_json={"subject": "s"},
        )
    )
    db_session.add(
        IntegrationJob(
            id=new_id("job"),
            email_id=email.id,
            routing_decision_id=decision.id,
            provider="jira",
            action="create",
            status="planned",
            payload_json={"summary": "s"},
        )
    )
    await db_session.commit()

    async def fake_hubspot(payload, action):
        return ("succeeded", 201, "ok", "hs-1")

    async def fake_jira(payload, action):
        return ("failed", 500, "boom", None)

    monkeypatch.setattr(integration_service, "hubspot_execute", fake_hubspot)
    monkeypatch.setattr(integration_service, "jira_execute", fake_jira)

    out = await integration_service.execute_jobs_for_email(db_session, email.id)
    assert out["succeeded"] == 1
    assert out["failed"] == 1
    refreshed = await db_session.get(Email, email.id)
    assert refreshed.status == "partial_failure"
    attempts = list((await db_session.execute(select(IntegrationAttempt))).scalars().all())
    assert len(attempts) == 2
