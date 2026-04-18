from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Email, EmailEvent, Tenant
from app.ingest.gmail_client import gmail_get_message
from app.ingest.normalize import normalize_gmail_message
from app.utils import new_id


@dataclass
class IngestResult:
    email: Email | None
    deduplicated: bool = False
    skipped_before_checkpoint: bool = False
    skipped_max_age: bool = False
    internal_ts_ms: int | None = None


async def ingest_gmail_message(
    session: AsyncSession,
    tenant: Tenant,
    message_id: str,
    *,
    min_internal_ts_ms: int | None,
    max_internal_age_seconds: int,
) -> IngestResult:
    msg = await gmail_get_message(message_id)
    n = normalize_gmail_message(msg)
    internal_ms = n.get("internal_ts_ms")
    if min_internal_ts_ms and internal_ms and internal_ms <= min_internal_ts_ms:
        return IngestResult(email=None, skipped_before_checkpoint=True, internal_ts_ms=internal_ms)
    if max_internal_age_seconds > 0 and internal_ms:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_sec = (now_ms - internal_ms) / 1000.0
        if age_sec > max_internal_age_seconds:
            return IngestResult(email=None, skipped_max_age=True, internal_ts_ms=internal_ms)

    q = select(Email).where(Email.provider_message_id == n["provider_message_id"])
    if n["rfc_message_id"]:
        q = select(Email).where((Email.provider_message_id == n["provider_message_id"]) | (Email.rfc_message_id == n["rfc_message_id"]))
    dedup = await session.execute(q)
    if dedup.scalar_one_or_none():
        return IngestResult(email=None, deduplicated=True, internal_ts_ms=internal_ms)

    email = Email(
        id=new_id("eml"),
        tenant_id=tenant.id,
        provider="gmail",
        provider_message_id=n["provider_message_id"],
        thread_id=n["thread_id"],
        rfc_message_id=n["rfc_message_id"],
        in_reply_to=n["in_reply_to"],
        references=n["references"],
        from_address=n["from_address"],
        to_addresses=n["to_addresses"],
        subject=n["subject"],
        body_text=n["body_text"],
        received_at=n["received_at"],
        provider_internal_ts_ms=n["internal_ts_ms"],
        status="received",
    )
    session.add(email)
    session.add(EmailEvent(id=new_id("evt"), email_id=email.id, event_type="received", detail_json={"provider": "gmail"}))
    await session.commit()
    return IngestResult(email=email, internal_ts_ms=internal_ms)
