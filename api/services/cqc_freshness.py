"""Evidence-backed aggregate freshness for authoritative CQC collections.

Only a completed, count-reconciled ``reconciliation`` run is a watermark.
Live provider timestamps and request time are deliberately not evidence.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Mapping

import asyncpg


FRESHNESS_SLA = timedelta(days=8)
_REQUIRED_COLUMNS = (
    "source_uri",
    "source_published_at",
    "source_retrieved_at",
    "source_checksum_sha256",
    "source_total_count",
    "checked_count",
    "success_count",
    "failure_count",
    "reconciled_at",
    "counts_reconciled",
)

_RUN_FIELDS = """
    id, status, started_at, completed_at, source_uri,
    source_published_at, source_retrieved_at, source_checksum_sha256,
    source_total_count, checked_count, success_count, failure_count,
    reconciled_at, counts_reconciled
"""


def _value(row: Mapping[str, Any] | None, key: str) -> Any:
    return row[key] if row is not None else None


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # Authoritative evidence columns are TIMESTAMPTZ. Treat an unexpected
        # naive value as unprovable rather than guessing that it is UTC.
        return None
    return value.astimezone(UTC)


def _timestamp(value: datetime | None) -> str | None:
    normalized = _utc(value)
    return normalized.isoformat() if normalized else None


def _published(value: date | datetime | None) -> str | None:
    # Preserve a CQC date as a date. In particular, never manufacture midnight.
    return value.isoformat() if value is not None else None


def _display_utc(value: datetime | None) -> str:
    normalized = _utc(value)
    if normalized is None:
        return "unknown"
    return f"{normalized.day} {normalized.strftime('%B %Y at %H:%M')} UTC"


def _coverage(checked: int | None, total: int | None) -> float | None:
    if checked is None or total is None:
        return None
    if checked < 0 or total < 0 or checked > total:
        return None
    if total == 0:
        return 100.0 if checked == 0 else None
    return round(checked * 100 / total, 5)


def _attempt_summary(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    total = _value(row, "source_total_count")
    checked = _value(row, "checked_count")
    return {
        "status": _value(row, "status"),
        "startedAt": _timestamp(_value(row, "started_at")),
        "completedAt": _timestamp(_value(row, "completed_at")),
        "totalSourceLocations": total,
        "checkedLocations": checked,
        "coveragePercentage": _coverage(checked, total),
        "successCount": _value(row, "success_count"),
        "failureCount": _value(row, "failure_count"),
        "countsReconciled": bool(_value(row, "counts_reconciled")),
    }


def _newer_incomplete_attempt(
    watermark: Mapping[str, Any] | None,
    latest_attempt: Mapping[str, Any] | None,
) -> bool:
    if watermark is None or latest_attempt is None:
        return latest_attempt is not None
    return bool(
        _value(latest_attempt, "id") != _value(watermark, "id")
        and (
            _value(latest_attempt, "status") != "completed"
            or not _complete_evidence(latest_attempt)
        )
    )


def _complete_evidence(row: Mapping[str, Any]) -> bool:
    total = _value(row, "source_total_count")
    checked = _value(row, "checked_count")
    success = _value(row, "success_count")
    failure = _value(row, "failure_count")
    checksum = _value(row, "source_checksum_sha256")
    return bool(
        _value(row, "source_uri")
        and _utc(_value(row, "source_retrieved_at")) is not None
        and _utc(_value(row, "reconciled_at")) is not None
        and isinstance(total, int)
        and isinstance(checked, int)
        and isinstance(success, int)
        and isinstance(failure, int)
        and total >= 0
        and checked == total
        and success == checked
        and failure == 0
        and _value(row, "counts_reconciled") is True
        and isinstance(checksum, str)
        and len(checksum) == 64
    )


def build_cqc_freshness(
    watermark: Mapping[str, Any] | None,
    latest_attempt: Mapping[str, Any] | None,
    *,
    now: datetime,
    schema_ready: bool = True,
) -> dict[str, Any]:
    """Build a public, aggregate-only result from persisted run evidence."""
    if not schema_ready:
        return {
            "status": "unknown",
            "source": None,
            "sourcePublishedAt": None,
            "sourceRetrievedAt": None,
            "reconciledAt": None,
            "totalSourceLocations": None,
            "checkedLocations": None,
            "successfullyCheckedLocations": None,
            "coveragePercentage": None,
            "successCount": None,
            "failureCount": None,
            "countsReconciled": False,
            "checksumSha256": None,
            "latestAttempt": None,
            "reason": "authoritative_freshness_schema_unavailable",
            "message": "Freshness cannot currently be confirmed because authoritative collection evidence is unavailable.",
        }

    latest_summary = _attempt_summary(latest_attempt)
    if watermark is None:
        status = "partial" if latest_attempt is not None else "unknown"
        reason = (
            "latest_authoritative_attempt_incomplete"
            if latest_attempt is not None
            else "no_completed_reconciled_authoritative_retrieval"
        )
        return {
            "status": status,
            "source": _value(latest_attempt, "source_uri"),
            "sourcePublishedAt": _published(_value(latest_attempt, "source_published_at")),
            "sourceRetrievedAt": None,
            "reconciledAt": None,
            "totalSourceLocations": None,
            "checkedLocations": None,
            "successfullyCheckedLocations": None,
            "coveragePercentage": None,
            "successCount": None,
            "failureCount": None,
            "countsReconciled": False,
            "checksumSha256": None,
            "latestAttempt": latest_summary,
            "reason": reason,
            "message": "Freshness cannot currently be confirmed because no completed, reconciled CQC retrieval is available.",
        }

    total = _value(watermark, "source_total_count")
    checked = _value(watermark, "checked_count")
    success = _value(watermark, "success_count")
    failure = _value(watermark, "failure_count")
    retrieved_at = _utc(_value(watermark, "source_retrieved_at"))
    coverage = _coverage(checked, total)
    common = {
        "source": _value(watermark, "source_uri"),
        "sourcePublishedAt": _published(_value(watermark, "source_published_at")),
        "sourceRetrievedAt": _timestamp(retrieved_at),
        "reconciledAt": _timestamp(_value(watermark, "reconciled_at")),
        "totalSourceLocations": total,
        "checkedLocations": checked,
        "successfullyCheckedLocations": success,
        "coveragePercentage": coverage,
        "successCount": success,
        "failureCount": failure,
        "countsReconciled": bool(_value(watermark, "counts_reconciled")),
        "checksumSha256": _value(watermark, "source_checksum_sha256"),
        "latestAttempt": latest_summary,
    }

    if _newer_incomplete_attempt(watermark, latest_attempt):
        return {
            "status": "partial",
            **common,
            "reason": "latest_authoritative_attempt_incomplete",
            "message": (
                "Freshness cannot currently be confirmed. "
                f"The last successful retrieval was {_display_utc(retrieved_at)}, "
                f"coverage was {coverage if coverage is not None else 'unknown'}%, "
                "and the latest authoritative attempt did not complete and reconcile."
            ),
        }

    if not _complete_evidence(watermark):
        return {
            "status": "unknown",
            **common,
            "reason": "completed_retrieval_evidence_incomplete",
            "message": "Freshness cannot currently be confirmed because the completed retrieval evidence is incomplete.",
        }

    assert retrieved_at is not None  # established by _complete_evidence
    if retrieved_at < _utc(now) - FRESHNESS_SLA:
        return {
            "status": "stale",
            **common,
            "reason": "latest_successful_retrieval_exceeds_freshness_sla",
            "message": (
                "Freshness cannot currently be confirmed. "
                f"The last successful retrieval was {_display_utc(retrieved_at)}, "
                f"coverage was {coverage}%, and it is older than the approved freshness window."
            ),
        }

    return {
        "status": "fresh",
        **common,
        "reason": None,
        "message": (
            f"CareGist data is current as of {_display_utc(retrieved_at)}. "
            f"The last successful CQC retrieval checked {checked:,} of {total:,} active locations, "
            "reconciled successfully, and completed without collection errors."
        ),
    }


async def get_cqc_freshness(
    conn: asyncpg.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read the authoritative watermark and latest attempt, then fail closed."""
    schema_ready = bool(
        await conn.fetchval(
            """
            SELECT COUNT(*) = $3
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = $1
              AND column_name = ANY($2::text[])
            """,
            "pipeline_runs",
            list(_REQUIRED_COLUMNS),
            len(_REQUIRED_COLUMNS),
        )
    )
    if not schema_ready:
        return build_cqc_freshness(None, None, now=now or datetime.now(UTC), schema_ready=False)

    # The pair must come from one MVCC snapshot. Otherwise a reconciliation
    # completing between the two reads can produce a contradictory watermark
    # and latest-attempt response.
    async with conn.transaction(isolation="repeatable_read", readonly=True):
        watermark = await conn.fetchrow(
            f"""
            SELECT {_RUN_FIELDS}
            FROM pipeline_runs
            WHERE run_type = 'reconciliation'
              AND status = 'completed'
              AND counts_reconciled = TRUE
              AND reconciled_at IS NOT NULL
              AND source_retrieved_at IS NOT NULL
            ORDER BY source_retrieved_at DESC, id DESC
            LIMIT 1
            """
        )
        latest_attempt = await conn.fetchrow(
            f"""
            SELECT {_RUN_FIELDS}
            FROM pipeline_runs
            WHERE run_type = 'reconciliation'
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """
        )
    return build_cqc_freshness(
        watermark,
        latest_attempt,
        now=now or datetime.now(UTC),
    )
