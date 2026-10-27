"""Private storage for a Territory Opportunity Brief's versioned buyer scope.

The objective text and exclusion identifiers live only in migration 071's tables.
Stripe metadata carries ``scope_versions.id`` as an opaque reference and nothing
else from the rules. Nothing here logs the rules.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from api.services.territory_brief import TerritoryScope

# Placeholder until the owner fixes the correction period (see the retention
# proposal). Exclusion identifiers are deleted this long after fulfilment.
DEFAULT_CORRECTION_WINDOW_DAYS = 30


def scope_rules_sha256(scope: TerritoryScope) -> str:
    """Canonical hash of the buyer rules, so they can be evidenced after purge."""
    canonical = json.dumps(
        {
            "buyer_objective": scope.buyer_objective,
            "excluded_provider_ids": sorted(scope.excluded_provider_ids),
            "excluded_location_ids": sorted(scope.excluded_location_ids),
            "rule_version": scope.rule_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def insert_scope_version(conn, order_id: str, scope: TerritoryScope, *, version: int = 1) -> str:
    """Store the buyer rules for an order and return the opaque scope reference."""
    if not scope.has_buyer_rules:
        raise ValueError("a scope without buyer rules has no version to store")
    row = await conn.fetchrow(
        """
        INSERT INTO territory_brief_scope_versions
            (order_id, version, supersedes_version, rule_version, buyer_objective,
             provider_exclusion_count, location_exclusion_count, scope_sha256)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        order_id,
        version,
        version - 1 if version > 1 else None,
        scope.rule_version,
        scope.buyer_objective,
        len(scope.excluded_provider_ids),
        len(scope.excluded_location_ids),
        scope_rules_sha256(scope),
    )
    scope_ref = str(row["id"])
    pairs = [("provider", i) for i in scope.excluded_provider_ids] + [
        ("location", i) for i in scope.excluded_location_ids
    ]
    for kind, cqc_id in pairs:
        await conn.execute(
            "INSERT INTO territory_brief_scope_exclusions (scope_version_id, id_kind, cqc_id) "
            "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            scope_ref,
            kind,
            cqc_id,
        )
    return scope_ref


async def load_scope_rules(conn, scope_ref: str, order_id: str) -> dict[str, Any]:
    """Return the rule fields for generation, checking the reference belongs to this order."""
    row = await conn.fetchrow(
        """
        SELECT id, rule_version, buyer_objective, scope_sha256,
               provider_exclusion_count, location_exclusion_count, exclusions_purged_at
        FROM territory_brief_scope_versions
        WHERE id = $1 AND order_id = $2
        """,
        scope_ref,
        order_id,
    )
    if not row:
        raise LookupError("scope reference does not belong to this order")
    expected = int(row["provider_exclusion_count"]) + int(row["location_exclusion_count"])
    exclusions = await conn.fetch(
        "SELECT id_kind, cqc_id FROM territory_brief_scope_exclusions WHERE scope_version_id = $1",
        scope_ref,
    )
    if row["exclusions_purged_at"] is not None or len(exclusions) != expected:
        # Regenerating without the full list would silently re-admit excluded accounts.
        raise LookupError("scope exclusions are no longer complete; the order cannot be regenerated")
    return {
        "scope_ref": str(row["id"]),
        "rule_version": int(row["rule_version"]),
        "buyer_objective": row["buyer_objective"],
        "excluded_provider_ids": sorted(r["cqc_id"] for r in exclusions if r["id_kind"] == "provider"),
        "excluded_location_ids": sorted(r["cqc_id"] for r in exclusions if r["id_kind"] == "location"),
    }


async def schedule_exclusion_purge(conn, scope_ref: str, *, days: int = DEFAULT_CORRECTION_WINDOW_DAYS) -> None:
    """Start the retention clock once the Brief is delivered. Idempotent."""
    await conn.execute(
        "UPDATE territory_brief_scope_versions "
        "SET exclusions_purge_after = NOW() + make_interval(days => $2) "
        "WHERE id = $1 AND exclusions_purge_after IS NULL",
        scope_ref,
        days,
    )


async def purge_expired_exclusions(conn, *, apply: bool = False) -> dict[str, int]:
    """Delete exclusion identifiers whose correction period has ended.

    The scope row, its hash and the counts are kept. A dry run only counts.
    """
    due = await conn.fetch(
        "SELECT id FROM territory_brief_scope_versions "
        "WHERE exclusions_purge_after IS NOT NULL AND exclusions_purge_after <= NOW() "
        "AND exclusions_purged_at IS NULL"
    )
    ids = [str(r["id"]) for r in due]
    deleted = 0
    if apply and ids:
        async with conn.transaction():
            for scope_ref in ids:
                status = await conn.execute(
                    "DELETE FROM territory_brief_scope_exclusions WHERE scope_version_id = $1", scope_ref
                )
                deleted += int(status.split()[-1])
                await conn.execute(
                    "UPDATE territory_brief_scope_versions SET exclusions_purged_at = NOW() WHERE id = $1",
                    scope_ref,
                )
    return {"scope_versions_due": len(ids), "exclusion_rows_deleted": deleted}
