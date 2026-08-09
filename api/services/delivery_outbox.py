"""Durable Radar delivery worker with no network I/O inside DB sessions."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg

from api.config import settings
from api.services.radar import OGL_ATTRIBUTION
from api.utils.crypto import maybe_decrypt
from api.utils.webhook_delivery import deliver_webhook


MAX_DELIVERY_ATTEMPTS = 8
PROCESSING_LEASE = timedelta(minutes=15)


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _matches_filter(row: dict[str, Any]) -> bool:
    config = _json_value(row.get("filter_config")) or {}
    if not isinstance(config, dict):
        return False
    region = config.get("region")
    event_types = config.get("event_types")
    if region and str(region).casefold() != str(row.get("region") or "").casefold():
        return False
    if event_types and row.get("event_type") not in event_types:
        return False
    return True


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    source_url = row.get("source_url") or f"https://www.cqc.org.uk/location/{row['location_id']}"
    return {
        "event": "radar.event.created",
        "event_id": str(row["public_event_id"]),
        "schema_version": int(row.get("schema_version") or 1),
        "event_type": row["event_type"],
        "entity": {
            "level": row.get("entity_level") or "location",
            "cqc_location_id": row["location_id"],
            "cqc_provider_id": row.get("provider_id"),
            "name": row.get("name"),
        },
        "change": {"old": _json_value(row.get("old_value")), "new": _json_value(row.get("new_value"))},
        "effective_at": row["effective_date"].isoformat(),
        "source_published_at": row["source_published_at"].isoformat() if row.get("source_published_at") else None,
        "observed_at": row["observed_at"].isoformat(),
        "source_checked_at": row["source_checked_at"].isoformat() if row.get("source_checked_at") else None,
        "source": {
            "url": source_url,
            "licence": OGL_ATTRIBUTION,
            "snapshot_sha256": row.get("source_snapshot_sha256"),
        },
    }


async def _claim_batch(database_url: str, batch_size: int) -> list[dict[str, Any]]:
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'delivery', true)")
            # A worker can die after claiming rows. Reclaim expired leases in the
            # same transaction so those events remain deliverable and idempotent.
            await conn.execute(
                """
                UPDATE delivery_outbox
                SET status = 'pending', locked_at = NULL,
                    last_error = 'delivery worker lease expired; retrying',
                    available_at = NOW(), updated_at = NOW()
                WHERE status = 'processing'
                  AND locked_at < NOW() - $1::interval
                """,
                PROCESSING_LEASE,
            )
            rows = await conn.fetch(
                """
                SELECT outbox.id, outbox.organization_id, outbox.delivery_subscription_id,
                       outbox.event_id AS ledger_id, outbox.attempt_count,
                       ds.endpoint, ds.signing_secret_ciphertext, ds.signing_secret_key_id,
                       ds.previous_signing_secret_ciphertext,
                       ds.previous_signing_secret_key_id, ds.previous_secret_valid_until,
                       ds.filter_config,
                       tel.public_event_id, tel.schema_version, tel.entity_level,
                       tel.event_type, tel.effective_date, tel.observed_at,
                       tel.old_value, tel.new_value, tel.source_published_at,
                       tel.source_checked_at, tel.source_url, tel.source_snapshot_sha256,
                       tel.location_id, tel.provider_id, cp.name, cp.region
                FROM delivery_outbox outbox
                JOIN delivery_subscriptions ds ON ds.id = outbox.delivery_subscription_id
                JOIN trusted_event_ledger tel ON tel.id = outbox.event_id
                LEFT JOIN care_providers cp ON cp.id = tel.location_id
                WHERE outbox.status = 'pending'
                  AND outbox.available_at <= NOW()
                  AND ds.active = TRUE
                  AND ds.delivery_type = 'webhook'
                ORDER BY outbox.available_at, outbox.created_at
                FOR UPDATE OF outbox SKIP LOCKED
                LIMIT $1
                """,
                batch_size,
            )
            ids = [row["id"] for row in rows]
            if ids:
                await conn.execute(
                    """
                    UPDATE delivery_outbox
                    SET status = 'processing', locked_at = NOW(), updated_at = NOW()
                    WHERE id = ANY($1::uuid[])
                    """,
                    ids,
                )
            return [dict(row) for row in rows]
    finally:
        await conn.close()


async def _record_result(
    database_url: str,
    row: dict[str, Any],
    *,
    success: bool,
    attempts: int,
    status_code: int | None,
    error_message: str | None,
) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'delivery', true)")
            total_attempts = int(row["attempt_count"] or 0) + max(attempts, 1)
            await conn.execute(
                """
                INSERT INTO delivery_attempts (outbox_id, attempt_number, response_status, error_message)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (outbox_id, attempt_number) DO NOTHING
                """,
                row["id"],
                total_attempts,
                status_code,
                (error_message or "")[:2000] or None,
            )
            if success:
                await conn.execute(
                    """
                    UPDATE delivery_outbox
                    SET status = 'delivered', attempt_count = $2, delivered_at = NOW(),
                        locked_at = NULL, last_error = NULL, updated_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                    total_attempts,
                )
                await conn.execute(
                    """
                    INSERT INTO delivery_cursors (organization_id, consumer_key, last_event_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (organization_id, consumer_key)
                    DO UPDATE SET last_event_id = EXCLUDED.last_event_id, updated_at = NOW()
                    """,
                    row["organization_id"],
                    str(row["delivery_subscription_id"]),
                    row["ledger_id"],
                )
            else:
                dead = total_attempts >= MAX_DELIVERY_ATTEMPTS
                backoff = min(3600, 30 * (2 ** min(total_attempts, 7)))
                await conn.execute(
                    """
                    UPDATE delivery_outbox
                    SET status = $2, attempt_count = $3,
                        available_at = $4, locked_at = NULL,
                        last_error = $5, updated_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                    "dead_letter" if dead else "pending",
                    total_attempts,
                    datetime.now(UTC) + timedelta(seconds=backoff),
                    (error_message or "delivery failed")[:2000],
                )
    finally:
        await conn.close()


async def process_delivery_outbox(database_url: str, *, batch_size: int = 50) -> dict[str, int]:
    if not settings.radar_delivery_enabled:
        return {"claimed": 0, "delivered": 0, "failed": 0, "filtered": 0}
    rows = await _claim_batch(database_url, batch_size)
    delivered = failed = filtered = 0
    for row in rows:
        if not _matches_filter(row):
            await _record_result(
                database_url,
                row,
                success=True,
                attempts=1,
                status_code=None,
                error_message=None,
            )
            filtered += 1
            continue
        encrypted_secret = row.get("signing_secret_ciphertext")
        if not encrypted_secret:
            await _record_result(
                database_url,
                row,
                success=False,
                attempts=1,
                status_code=None,
                error_message="delivery signing secret is missing",
            )
            failed += 1
            continue
        secrets = [maybe_decrypt(encrypted_secret, settings.webhook_secret_key)]
        previous_secret = row.get("previous_signing_secret_ciphertext")
        previous_valid_until = row.get("previous_secret_valid_until")
        if (
            previous_secret
            and previous_valid_until
            and previous_valid_until > datetime.now(UTC)
        ):
            secrets.append(maybe_decrypt(previous_secret, settings.webhook_secret_key))
        success, attempts, status_code, error_message = await deliver_webhook(
            row["endpoint"],
            secrets,
            _payload(row),
            return_metadata=True,
        )
        await _record_result(
            database_url,
            row,
            success=success,
            attempts=attempts,
            status_code=status_code,
            error_message=error_message,
        )
        if success:
            delivered += 1
        else:
            failed += 1
    return {"claimed": len(rows), "delivered": delivered, "failed": failed, "filtered": filtered}
