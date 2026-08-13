"""Prometheus metrics for the API (F-47).

Exposes request latency/volume by tier, plus operational gauges the audit called
out (pending-email depth, webhook delivery outcomes, rate-limit 429s). Import is
side-effect-free; the collectors register lazily on first use. If
``prometheus_client`` is not installed the module degrades to no-ops so the app
still runs in minimal environments.
"""

from __future__ import annotations

import logging
import time
from contextvars import ContextVar

logger = logging.getLogger("caregist.metrics")

_REQUEST_TIER: ContextVar[str] = ContextVar("caregist_request_tier", default="unknown")

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _ENABLED = True
except ImportError:  # pragma: no cover - prometheus_client is a hard dep in prod
    _ENABLED = False
    CONTENT_TYPE_LATEST = "text/plain"


if _ENABLED:
    REQUEST_LATENCY = Histogram(
        "caregist_request_duration_seconds",
        "HTTP request latency in seconds.",
        labelnames=("method", "route", "tier"),
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    REQUEST_TOTAL = Counter(
        "caregist_requests_total",
        "HTTP requests by status class and tier.",
        labelnames=("method", "route", "status", "tier"),
    )
    RATE_LIMITED_TOTAL = Counter(
        "caregist_rate_limited_total",
        "Requests rejected with HTTP 429.",
        labelnames=("route", "tier"),
    )
    WEBHOOK_DELIVERY_TOTAL = Counter(
        "caregist_webhook_delivery_total",
        "Outbound webhook delivery outcomes.",
        labelnames=("outcome",),
    )
    PENDING_EMAILS = Gauge(
        "caregist_pending_emails",
        "Current pending_emails queue depth by status.",
        labelnames=("status",),
    )
    CRM_AI_WORKER_AGE_SECONDS = Gauge(
        "caregist_crm_ai_worker_age_seconds",
        "Seconds since the CRM AI worker heartbeat.",
    )
    CRM_AI_MONTHLY_SPEND_USD = Gauge(
        "caregist_crm_ai_monthly_spend_usd",
        "Recorded DeepSeek usage cost in the current UTC month.",
    )
    CRM_RETENTION_EXPIRED_BACKLOG = Gauge(
        "caregist_crm_retention_expired_backlog",
        "CRM recordings at or beyond expiry that are not confirmed deleted.",
    )
    CRM_RETENTION_FAILURES = Gauge(
        "caregist_crm_retention_failures",
        "Expired CRM recordings currently carrying deletion errors.",
    )
    CRM_TPS_STALE_ORGANIZATIONS = Gauge(
        "caregist_crm_tps_stale_organizations",
        "Enabled CRM organisations whose TPS automation has missed its run SLA.",
    )
    CRM_TPS_FAILED_ORGANIZATIONS = Gauge(
        "caregist_crm_tps_failed_organizations",
        "Enabled CRM organisations whose latest TPS automation run reported an error.",
    )
    CRM_TPS_PENDING_JOBS = Gauge(
        "caregist_crm_tps_pending_jobs",
        "TPS screening jobs waiting or currently processing.",
    )
    CRM_TPS_REVIEW_JOBS = Gauge(
        "caregist_crm_tps_review_jobs",
        "TPS screening jobs requiring owner or administrator review.",
    )


def observe_request(*, method: str, route: str, tier: str, status: int, duration: float) -> None:
    if not _ENABLED:
        return
    status_class = f"{status // 100}xx"
    REQUEST_LATENCY.labels(method, route, tier).observe(duration)
    REQUEST_TOTAL.labels(method, route, status_class, tier).inc()
    if status == 429:
        RATE_LIMITED_TOTAL.labels(route, tier).inc()


def set_request_tier(tier: str | None) -> None:
    """Attach the authenticated tier to the current request context."""
    _REQUEST_TIER.set(tier or "unknown")


def observe_webhook_delivery(success: bool) -> None:
    if not _ENABLED:
        return
    WEBHOOK_DELIVERY_TOTAL.labels("success" if success else "failure").inc()


def set_pending_emails(status: str, count: int) -> None:
    if not _ENABLED:
        return
    PENDING_EMAILS.labels(status).set(count)


def set_crm_operations(
    *, worker_age_seconds: float | None, monthly_spend_usd: float,
    expired_backlog: int, retention_failures: int, tps_stale_organizations: int = 0,
    tps_failed_organizations: int = 0, tps_pending_jobs: int = 0,
    tps_review_jobs: int = 0,
) -> None:
    if not _ENABLED:
        return
    if worker_age_seconds is not None:
        CRM_AI_WORKER_AGE_SECONDS.set(worker_age_seconds)
    CRM_AI_MONTHLY_SPEND_USD.set(monthly_spend_usd)
    CRM_RETENTION_EXPIRED_BACKLOG.set(expired_backlog)
    CRM_RETENTION_FAILURES.set(retention_failures)
    CRM_TPS_STALE_ORGANIZATIONS.set(tps_stale_organizations)
    CRM_TPS_FAILED_ORGANIZATIONS.set(tps_failed_organizations)
    CRM_TPS_PENDING_JOBS.set(tps_pending_jobs)
    CRM_TPS_REVIEW_JOBS.set(tps_review_jobs)


def render_latest() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    if not _ENABLED:
        return b"# prometheus_client not installed\n", CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST


class MetricsMiddleware:
    """Pure-ASGI middleware that records latency/volume per request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not _ENABLED:
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_holder = {"status": 500}
        token = _REQUEST_TIER.set("unknown")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            route = _route_label(scope)
            tier = _REQUEST_TIER.get()
            observe_request(
                method=scope.get("method", "GET"),
                route=route,
                tier=tier,
                status=status_holder["status"],
                duration=duration,
            )
            _REQUEST_TIER.reset(token)


def _route_label(scope) -> str:
    """Return the matched route template (low cardinality).

    Falls back to "unmatched" rather than the raw path so unmatched/404 traffic
    (which can contain arbitrary IDs/slugs) cannot explode label cardinality.
    """
    route = scope.get("route")
    path_format = getattr(route, "path_format", None) or getattr(route, "path", None)
    return path_format or "unmatched"
