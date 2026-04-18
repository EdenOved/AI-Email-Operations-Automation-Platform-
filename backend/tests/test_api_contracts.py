import pytest
from sqlalchemy import select

from app.db.models import ApprovalRequest, Email, EvalRun, Tenant
from app.utils import new_id


@pytest.mark.asyncio
async def test_operator_core_endpoints(api_client, session_factory):
    async with session_factory() as session:
        tenant = (await session.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one()
        email = Email(
            id=new_id("eml"),
            tenant_id=tenant.id,
            provider="gmail",
            provider_message_id="m-api-1",
            from_address="x@example.com",
            subject="Need help",
            body_text="Please help",
            status="awaiting_approval",
        )
        session.add(email)
        session.add(
            ApprovalRequest(
                id=new_id("apr"),
                email_id=email.id,
                status="pending",
                reason="low_confidence",
                proposed_route="crm_only",
                snapshot_json={},
            )
        )
        session.add(
            EvalRun(
                id=new_id("evr"),
                status="completed",
                model="heuristic",
                judge_model=None,
                pass_rate=1.0,
                case_total=1,
                route_pass=1,
                route_fail=0,
                judge_avg_overall=None,
            )
        )
        await session.commit()

    inbox = api_client.get("/api/v1/operator/inbox")
    assert inbox.status_code == 200
    assert "items" in inbox.json()

    detail = api_client.get(f"/api/v1/operator/cases/{email.id}")
    assert detail.status_code == 200
    assert "email" in detail.json()

    approvals = api_client.get("/api/v1/operator/approvals/pending")
    assert approvals.status_code == 200
    assert "items" in approvals.json()

    ops = api_client.get("/api/v1/operator/operations/summary")
    assert ops.status_code == 200
    assert "business_value" in ops.json()

    evals = api_client.get("/api/v1/operator/evals/dataset")
    assert evals.status_code == 200
    assert "items" in evals.json()
