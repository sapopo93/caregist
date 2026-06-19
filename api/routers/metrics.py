"""
Prometheus /metrics endpoint for CareGist API.

Exposes:
  Counters:
    caregist_requests_total{method, endpoint, status}
    caregist_rate_limit_rejections_total
    caregist_webhook_failures_total

  Histograms:
    caregist_request_duration_seconds{method, endpoint}

  Gauges:
    caregist_email_queue_depth
    caregist_pipeline_freshness_seconds

Usage:
  Prometheus scrape target: http://<host>:8000/metrics
  Add the router in api/main.py:
    from api.routers import metrics
    app.include_router(metrics.router)
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PROMETHEUS_AVAILABLE = False

router = APIRouter(tags=["observability"])

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

if _PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "caregist_requests_total",
        "Total HTTP requests handled by the CareGist API",
        ["method", "endpoint", "status"],
    )

    REQUEST_LATENCY = Histogram(
        "caregist_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    RATE_LIMIT_REJECTIONS = Counter(
        "caregist_rate_limit_rejections_total",
        "Total requests rejected by the rate limiter",
    )

    WEBHOOK_FAILURES = Counter(
        "caregist_webhook_failures_total",
        "Total webhook delivery failures",
    )

    EMAIL_QUEUE_DEPTH = Gauge(
        "caregist_email_queue_depth",
        "Number of emails currently pending in the pending_emails queue",
    )

    PIPELINE_FRESHNESS = Gauge(
        "caregist_pipeline_freshness_seconds",
        "Seconds since the new-registration pipeline last completed successfully (lower is fresher)",
    )
else:
    # Stubs so callers never have to guard on availability
    class _Noop:
        def labels(self, **_kw):
            return self
        def inc(self, *a, **kw):
            pass
        def observe(self, *a, **kw):
            pass
        def set(self, *a, **kw):
            pass
        def time(self):
            import contextlib
            return contextlib.nullcontext()

    REQUEST_COUNT = _Noop()
    REQUEST_LATENCY = _Noop()
    RATE_LIMIT_REJECTIONS = _Noop()
    WEBHOOK_FAILURES = _Noop()
    EMAIL_QUEUE_DEPTH = _Noop()
    PIPELINE_FRESHNESS = _Noop()


# ---------------------------------------------------------------------------
# Middleware helper — call from main.py middleware to record every request
# ---------------------------------------------------------------------------

async def record_request_metrics(request: Request, call_next):
    """
    ASGI middleware that records request count and latency.

    Wire up in api/main.py:

        from api.routers.metrics import record_request_metrics

        @app.middleware("http")
        async def prometheus_middleware(request, call_next):
            return await record_request_metrics(request, call_next)
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    # Use the route path template if available, else the raw path
    route = request.scope.get("route")
    endpoint = route.path if isinstance(route, APIRoute) else request.url.path

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=str(response.status_code),
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)

    return response


# ---------------------------------------------------------------------------
# /metrics route
# ---------------------------------------------------------------------------

@router.get(
    "/metrics",
    response_class=Response,
    include_in_schema=False,
    summary="Prometheus metrics",
)
async def metrics_endpoint() -> Response:
    """
    Expose all registered Prometheus metrics in the standard text format.
    Point your Prometheus scrape config at this path.

    Example scrape config:

        scrape_configs:
          - job_name: caregist_api
            static_configs:
              - targets: ['<ec2-private-ip>:8000']
    """
    if not _PROMETHEUS_AVAILABLE:
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain; version=0.0.4",
            status_code=503,
        )
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
