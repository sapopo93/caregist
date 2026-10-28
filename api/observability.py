"""Content-minimised backend error reporting and an opt-in rollout receipt."""

from __future__ import annotations

import os
from typing import Any


def scrub_error_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Keep error types and stack locations, withhold customer/request content.

    Exception messages and local variables can contain SQL parameters, tokens,
    email addresses or enquiry text even with send_default_pii disabled.
    """
    for key in (
        "request", "user", "extra", "contexts", "breadcrumbs", "logentry",
        "message", "tags", "transaction", "transaction_info", "server_name",
    ):
        event.pop(key, None)
    for exception in event.get("exception", {}).get("values", []):
        exception["value"] = "Exception message withheld by CareGist"
        exception.get("mechanism", {}).pop("data", None)
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    return event


class CareGistSentryVerification(Exception):
    """Synthetic rollout receipt; never raised into a customer request."""


def configure_sentry(sdk: Any, dsn: str, *, production: bool) -> bool:
    if sdk is None or not dsn:
        return False
    release = os.environ.get("VERCEL_GIT_COMMIT_SHA") or "local"
    sdk.init(
        dsn=dsn,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        enable_logs=False,
        before_send=scrub_error_event,
        environment="production" if production else "development",
        release=f"caregist-api@{release}",
    )
    # A release-pinned, explicitly requested rollout check, off by default.
    # This records a handled info event; it cannot return a customer-facing 500.
    if production and release != "local" and os.environ.get("SENTRY_VERIFY_RELEASE") == release:
        with sdk.new_scope() as scope:
            scope.level = "info"
            sdk.capture_exception(CareGistSentryVerification())
            sdk.flush(timeout=2)
    return True
