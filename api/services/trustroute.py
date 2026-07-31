"""Bounded, fail-closed delivery of CareGist outbox events to TrustRoute."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from api.database import get_connection

logger = logging.getLogger("caregist.trustroute")
MAX_ATTEMPTS = 8


@dataclass(frozen=True)
class TrustRouteConfig:
    enabled: bool
    base_url: str
    organization_id: str
    api_key: str
    batch_size: int = 25

    def validate(self) -> None:
        if not self.enabled:
            return
        parsed = urlparse(self.base_url)
        local = parsed.hostname in {"localhost", "127.0.0.1"}
        if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
            raise ValueError("TrustRoute base URL must use HTTPS outside localhost.")
        if not self.organization_id or not self.api_key:
            raise ValueError("TrustRoute organization ID and API key are required when sync is enabled.")
        if not 1 <= self.batch_size <= 100:
            raise ValueError("TrustRoute batch size must be between 1 and 100.")


async def _claim(batch_size: int) -> list[dict[str, Any]]:
    async with get_connection() as connection:
        rows = await connection.fetch(
            """
            WITH candidates AS (
              SELECT outbox_event_id FROM trustroute_outbox
              WHERE (status='pending' OR (status='processing' AND lease_until < now()))
                AND next_attempt_at <= now()
              ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT $1
            )
            UPDATE trustroute_outbox o SET status='processing', claim_token=gen_random_uuid(),
              lease_until=now()+interval '60 seconds', attempt_count=attempt_count+1, updated_at=now()
            FROM candidates c WHERE o.outbox_event_id=c.outbox_event_id
            RETURNING o.*
            """,
            batch_size,
        )
    return [dict(row) for row in rows]


async def _complete(event: dict[str, Any]) -> bool:
    async with get_connection() as connection:
        result = await connection.execute(
            """
            UPDATE trustroute_outbox SET status='succeeded',claim_token=NULL,lease_until=NULL,
              delivered_at=now(),last_error_code=NULL,updated_at=now()
            WHERE outbox_event_id=$1 AND claim_token=$2 AND status='processing'
            """,
            event["outbox_event_id"], event["claim_token"],
        )
    return result == "UPDATE 1"


async def _fail(event: dict[str, Any], error_code: str) -> None:
    dead = int(event["attempt_count"]) >= MAX_ATTEMPTS
    async with get_connection() as connection:
        await connection.execute(
            """
            UPDATE trustroute_outbox SET status=$3,claim_token=NULL,lease_until=NULL,
              next_attempt_at=now() + make_interval(secs => LEAST(3600, power(2, attempt_count)::int)),
              last_error_code=$4,updated_at=now()
            WHERE outbox_event_id=$1 AND claim_token=$2 AND status='processing'
            """,
            event["outbox_event_id"], event["claim_token"], "dead" if dead else "pending", error_code[:100],
        )


async def drain_trustroute_outbox(config: TrustRouteConfig) -> dict[str, int | bool]:
    config.validate()
    if not config.enabled:
        return {"enabled": False, "claimed": 0, "succeeded": 0, "failed": 0}
    events = await _claim(config.batch_size)
    succeeded = failed = 0
    headers = {"X-Organization-ID": config.organization_id, "Authorization": f"Bearer {config.api_key}"}
    async with httpx.AsyncClient(base_url=config.base_url.rstrip("/"), timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        for event in events:
            body = {
                "schema_version": 1,
                "source_event_id": event["source_event_id"],
                "event_type": event["event_type"],
                "occurred_at": event["occurred_at"].isoformat(),
                "payload": event["payload"],
            }
            try:
                response = await client.post("/api/v1/integrations/caregist/events", headers=headers, json=body)
                response.raise_for_status()
                if await _complete(event):
                    succeeded += 1
            except (httpx.HTTPError, ValueError) as exc:
                await _fail(event, type(exc).__name__)
                failed += 1
                logger.warning("TrustRoute event delivery failed", extra={"error_type": type(exc).__name__})
    return {"enabled": True, "claimed": len(events), "succeeded": succeeded, "failed": failed}
