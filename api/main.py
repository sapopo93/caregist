"""CareGist API — UK care provider directory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import close_pool, init_pool
from api.routers import auth, billing, health, providers, regions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    billing.init_stripe()
    yield
    await close_pool()


app = FastAPI(
    title="CareGist API",
    description="UK care provider directory powered by CQC data. "
    "55,818 providers with ratings, inspections, and quality scoring.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(providers.router)
app.include_router(regions.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
