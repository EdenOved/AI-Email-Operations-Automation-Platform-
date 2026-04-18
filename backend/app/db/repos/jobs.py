from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IntegrationJob


async def latest_success_for_provider(session: AsyncSession, email_id: str, provider: str) -> IntegrationJob | None:
    q = await session.execute(
        select(IntegrationJob)
        .where(
            and_(
                IntegrationJob.email_id == email_id,
                IntegrationJob.provider == provider,
                IntegrationJob.status == "succeeded",
            )
        )
        .order_by(desc(IntegrationJob.updated_at))
        .limit(1)
    )
    return q.scalar_one_or_none()
