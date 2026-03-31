"""CareGist API — UK care provider directory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import close_pool, init_pool
from api.routers import admin, api_applications, auth, billing, city_pages, claims, comparisons, enquiries, health, providers, public_tools, region_stats, regions, reviews, subscribe


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
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type", "Accept"],
)

import logging

from fastapi.responses import JSONResponse

_logger = logging.getLogger("caregist.app")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    _logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(claims.router)
app.include_router(reviews.router)
app.include_router(enquiries.router)
app.include_router(admin.router)
app.include_router(providers.router)
app.include_router(regions.router)
app.include_router(subscribe.router)
app.include_router(comparisons.router)
app.include_router(api_applications.router)
app.include_router(public_tools.router)
app.include_router(region_stats.router)
app.include_router(city_pages.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
