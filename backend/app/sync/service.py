from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.repos.tenants import get_by_slug
from app.ingest.gmail_client import gmail_list_message_ids
from app.ingest.service import ingest_gmail_message
from app.process.service import run_pipeline_for_email
from app.integrations.service import execute_jobs_for_email


@dataclass
class SyncResult:
    fetched: int = 0
    ingested_new: int = 0
    deduplicated: int = 0
    skipped_before_checkpoint: int = 0
    skipped_max_age: int = 0
    processed: int = 0
    failed: int = 0
    checkpoint_bootstrapped: bool = False
    checkpoint_advanced: bool = False


async def _bootstrap_checkpoint_if_needed(session: AsyncSession, tenant) -> tuple[int, bool]:
    s = get_settings()
    existing = get_checkpoint_ms(tenant)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if s.gmail_reset_ingest_watermark:
        set_checkpoint_ms(tenant, now_ms)
        await session.commit()
        return now_ms, True
    if not s.gmail_ingest_watermark_enabled:
        return 0, False
    if existing is None:
        set_checkpoint_ms(tenant, now_ms)
        await session.commit()
        return now_ms, True
    return existing, False


def get_checkpoint_ms(tenant) -> int | None:
    raw = dict(tenant.settings_json or {}).get("gmail_sync_checkpoint_ms")
    if raw is None:
        return None
    try:
        return int(raw)
    except Exception:
        return None


def set_checkpoint_ms(tenant, value: int) -> None:
    settings = dict(tenant.settings_json or {})
    settings["gmail_sync_checkpoint_ms"] = int(value)
    tenant.settings_json = settings


async def run_gmail_sync_cycle(session: AsyncSession, tenant_slug: str) -> dict:
    s = get_settings()
    result = SyncResult()
    if not s.email_ingest_enabled:
        return {"note": "ingest_disabled", **result.__dict__}
    tenant = await get_by_slug(session, tenant_slug)
    if tenant is None:
        raise RuntimeError(f"tenant {tenant_slug!r} not found")

    min_checkpoint_ms, bootstrapped = await _bootstrap_checkpoint_if_needed(session, tenant)
    result.checkpoint_bootstrapped = bootstrapped
    if bootstrapped:
        return result.__dict__

    ids = await gmail_list_message_ids(max_results=s.gmail_max_messages_per_poll, query=s.gmail_poll_query)
    result.fetched = len(ids)
    max_seen = min_checkpoint_ms
    for message_id in ids:
        try:
            ingest = await ingest_gmail_message(
                session,
                tenant,
                message_id,
                min_internal_ts_ms=min_checkpoint_ms if s.gmail_ingest_watermark_enabled else None,
                max_internal_age_seconds=s.gmail_ingest_max_internal_age_seconds,
            )
            if ingest.internal_ts_ms and ingest.internal_ts_ms > max_seen:
                max_seen = ingest.internal_ts_ms
            if ingest.skipped_before_checkpoint:
                result.skipped_before_checkpoint += 1
                continue
            if ingest.skipped_max_age:
                result.skipped_max_age += 1
                continue
            if ingest.deduplicated:
                result.deduplicated += 1
                continue
            if ingest.email is None:
                continue
            result.ingested_new += 1
            await run_pipeline_for_email(session, ingest.email)
            if ingest.email.status in ("routed", "partial_failure", "failed"):
                await execute_jobs_for_email(session, ingest.email.id)
            result.processed += 1
        except Exception:
            await session.rollback()
            result.failed += 1
    if s.gmail_ingest_watermark_enabled and max_seen > min_checkpoint_ms:
        set_checkpoint_ms(tenant, max_seen)
        await session.commit()
        result.checkpoint_advanced = True
    return result.__dict__
