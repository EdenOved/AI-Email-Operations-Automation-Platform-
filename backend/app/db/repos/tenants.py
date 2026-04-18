from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tenant
from app.utils import new_id


async def get_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    q = await session.execute(select(Tenant).where(Tenant.slug == slug))
    return q.scalar_one_or_none()


async def ensure_demo(session: AsyncSession) -> Tenant:
    existing = await get_by_slug(session, "demo")
    if existing:
        return existing
    tenant = Tenant(id=new_id("tnt"), name="Demo", slug="demo", settings_json={})
    session.add(tenant)
    await session.commit()
    return tenant
