import pytest
from sqlalchemy import select

from app.db.models import Email, Tenant
from app.ingest import service as ingest_service
from app.sync import service as sync_service


def _gmail_payload(msg_id: str, internal_ms: int) -> dict:
    return {
        "id": msg_id,
        "threadId": "thr-1",
        "internalDate": str(internal_ms),
        "payload": {
            "headers": [
                {"name": "From", "value": "a@example.com"},
                {"name": "To", "value": "b@example.com"},
                {"name": "Subject", "value": "Test"},
                {"name": "Message-Id", "value": f"<{msg_id}@example.com>"},
            ],
            "body": {"data": ""},
        },
    }


@pytest.mark.asyncio
async def test_ingest_respects_checkpoint_and_dedup(db_session, monkeypatch):
    tenant = (await db_session.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one()

    async def fake_get_message(message_id: str):
        return _gmail_payload(message_id, 2_000)

    monkeypatch.setattr(ingest_service, "gmail_get_message", fake_get_message)

    first = await ingest_service.ingest_gmail_message(
        db_session,
        tenant,
        "m1",
        min_internal_ts_ms=1_000,
        max_internal_age_seconds=0,
    )
    assert first.email is not None

    dup = await ingest_service.ingest_gmail_message(
        db_session,
        tenant,
        "m1",
        min_internal_ts_ms=1_000,
        max_internal_age_seconds=0,
    )
    assert dup.deduplicated is True

    skipped = await ingest_service.ingest_gmail_message(
        db_session,
        tenant,
        "m2",
        min_internal_ts_ms=2_000,
        max_internal_age_seconds=0,
    )
    assert skipped.skipped_before_checkpoint is True


@pytest.mark.asyncio
async def test_checkpoint_reset_bootstrap_writes_now(db_session, monkeypatch):
    tenant = (await db_session.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one()
    tenant.settings_json = {"gmail_sync_checkpoint_ms": 111}
    await db_session.commit()

    class S:
        gmail_reset_ingest_watermark = True
        gmail_ingest_watermark_enabled = True

    monkeypatch.setattr(sync_service, "get_settings", lambda: S())
    value, bootstrapped = await sync_service._bootstrap_checkpoint_if_needed(db_session, tenant)
    assert bootstrapped is True
    assert value > 111
