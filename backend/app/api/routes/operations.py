from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.operator.queries import integration_status, operations_summary

router = APIRouter(prefix="/api/v1/operator", tags=["operations"])


@router.get("/operations/summary")
async def ops_summary(session: AsyncSession = Depends(get_session)) -> dict:
    return await operations_summary(session)


@router.get("/integrations/status")
async def ops_integrations_status(live: bool = Query(default=False)) -> dict:
    return await integration_status(live=live)
