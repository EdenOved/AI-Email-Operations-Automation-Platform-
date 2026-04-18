from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GoldenCaseCandidate


async def list_golden_candidates(session: AsyncSession) -> list[GoldenCaseCandidate]:
    return list((await session.execute(select(GoldenCaseCandidate))).scalars().all())
