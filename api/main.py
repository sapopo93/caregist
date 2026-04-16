"""CareGist API — the intelligence layer for UK care-provider data."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - optional observability dependency in local test envs
    sentry_sdk = None
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import close_pool, init_pool
from api.logging_config import setup_logging

# Structured JSON logs in production, human-readable locally
setup_logging(json_output="localhost" not in settings.database_url)
from api.routers import admin, analytics, api_applications, auth, billing, city_pages, claims, comparisons, enquiries, feed, groups, health, internal, provider_profile, providers, public_tools, region_stats, regions, reviews, sitemaps, subscribe, webhooks

if sentry_sdk and settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production" if "localhost" not in settings.database_url else "development",
        release=f"caregist-api@1.0.0",
    )


async def _email_drain_loop() -> None:
    """Drain the pending_emails queue every 30 seconds, independent of health checks."""
    from api.utils.email_queue import process_email_queue
    import logging as _logging
    _log = _logging.getLogger("caregist.email_drain")
    while True:
        try:
            await asyncio.sleep(30)
            await process_email_queue(batch_size=50)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            _log.warning("Email drain loop error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    billing.init_stripe()
    drain_task = asyncio.create_task(_email_drain_loop())
    yield
    drain_task.cancel()
    try:
        await drain_task
    except asyncio.CancelledError:
        pass
    await close_pool()


_is_local = "localhost" in settings.database_url

app = FastAPI(
    title="CareGist API",
    description="Ledger-backed UK care-provider intelligence built for recurring new-registration workflows, "
    "dashboard delivery, exports, digests, and API integration on top of the CQC register.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _is_local else None,
    redoc_url="/redoc" if _is_local else None,
    openapi_url="/openapi.json" if _is_local else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type", "Accept"],
)

import logging

from fastapi.responses import JSONResponse

_logger = logging.getLogger("caregist.app")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    _logger.error("Unhandled exception: %s", exc, exc_info=True)
    if sentry_sdk:
        sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(health.router)
app.include_router(internal.router)
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(billing.router)
app.include_router(claims.router)
app.include_router(reviews.router)
app.include_router(enquiries.router)
app.include_router(admin.router)
app.include_router(groups.router)
app.include_router(provider_profile.router)
app.include_router(providers.router)
app.include_router(feed.router)
app.include_router(regions.router)
app.include_router(subscribe.router)
app.include_router(comparisons.router)
app.include_router(api_applications.router)
app.include_router(public_tools.router)
app.include_router(region_stats.router)
app.include_router(city_pages.router)
app.include_router(sitemaps.router)
app.include_router(webhooks.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
