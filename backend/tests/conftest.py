import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Tenant
from app.db.session import Base, get_session
from app.main import app
from app.utils import new_id


@pytest_asyncio.fixture()
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(Tenant(id=new_id("tnt"), name="Demo", slug="demo", settings_json={}))
        await session.commit()
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture()
def api_client(session_factory):
    import app.main as main_mod

    async def _override_get_session():
        async with session_factory() as session:
            yield session

    async def _ensure_demo_noop(_session):
        return None

    main_mod.SessionLocal = session_factory
    main_mod.ensure_demo = _ensure_demo_noop
    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
