import pytest

from app.sync.service import _bootstrap_checkpoint_if_needed


class DummySession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class DummyTenant:
    def __init__(self, settings_json=None) -> None:
        self.settings_json = settings_json or {}


@pytest.mark.asyncio
async def test_bootstrap_checkpoint_first_run(monkeypatch):
    from app.sync import service as sync_mod

    class S:
        gmail_reset_ingest_watermark = False
        gmail_ingest_watermark_enabled = True

    monkeypatch.setattr(sync_mod, "get_settings", lambda: S())
    session = DummySession()
    tenant = DummyTenant({})
    value, bootstrapped = await _bootstrap_checkpoint_if_needed(session, tenant)
    assert bootstrapped is True
    assert isinstance(value, int)
    assert "gmail_sync_checkpoint_ms" in tenant.settings_json
    assert session.commits == 1
