from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Email


async def get_by_id(session: AsyncSession, email_id: str) -> Email | None:
    return await session.get(Email, email_id)


async def get_latest_in_thread(session: AsyncSession, tenant_id: str, thread_id: str, exclude_email_id: str) -> Email | None:
    q = await session.execute(
        select(Email)
        .where(and_(Email.tenant_id == tenant_id, Email.thread_id == thread_id, Email.id != exclude_email_id))
        .order_by(desc(Email.created_at))
        .limit(1)
    )
    return q.scalar_one_or_none()
