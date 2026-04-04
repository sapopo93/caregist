"""CareGist API — UK care provider directory."""

from __future__ import annotations

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import close_pool, init_pool
from api.logging_config import setup_logging

# Structured JSON logs in production, human-readable locally
setup_logging(json_output="localhost" not in settings.database_url)
from api.routers import admin, api_applications, auth, billing, city_pages, claims, comparisons, enquiries, groups, health, provider_profile, providers, public_tools, region_stats, regions, reviews, subscribe

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production" if "localhost" not in settings.database_url else "development",
        release=f"caregist-api@1.0.0",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    billing.init_stripe()
    yield
    await close_pool()


_is_local = "localhost" in settings.database_url

app = FastAPI(
    title="CareGist API",
    description="UK care provider directory powered by CQC data. "
    "55,818 providers with ratings, inspections, and quality scoring.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _is_local else None,
    redoc_url="/redoc" if _is_local else None,
    openapi_url="/openapi.json" if _is_local else None,
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
    sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(health.router)


# Process email queue on a background schedule triggered by health checks
import asyncio

_email_task_running = False


@app.middleware("http")
async def email_queue_middleware(request, call_next):
    global _email_task_running
    response = await call_next(request)
    # Piggyback on health check to drain the email queue
    if request.url.path == "/api/v1/health" and not _email_task_running:
        _email_task_running = True
        try:
            from api.utils.email_queue import process_email_queue
            asyncio.create_task(_process_emails())
        except Exception:
            _email_task_running = False
    return response


async def _process_emails():
    global _email_task_running
    try:
        from api.utils.email_queue import process_email_queue
        await process_email_queue(batch_size=20)
    except Exception as exc:
        _logger.warning("Email queue processing error: %s", exc)
    finally:
        _email_task_running = False
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(claims.router)
app.include_router(reviews.router)
app.include_router(enquiries.router)
app.include_router(admin.router)
app.include_router(groups.router)
app.include_router(provider_profile.router)
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
