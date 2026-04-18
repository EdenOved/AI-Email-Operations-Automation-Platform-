from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.approvals import router as approvals_router
from app.api.routes.cases import router as cases_router
from app.api.routes.evals import router as evals_router
from app.api.routes.health import router as health_router
from app.api.routes.operations import router as operations_router
from app.api.routes.webhooks import router as webhooks_router
from app.core.logging import configure_logging
from app.db.repos.tenants import ensure_demo
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    async with SessionLocal() as session:
        await ensure_demo(session)
    yield


app = FastAPI(title="email-ops-clean", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(cases_router)
app.include_router(approvals_router)
app.include_router(operations_router)
app.include_router(evals_router)
app.include_router(webhooks_router)
