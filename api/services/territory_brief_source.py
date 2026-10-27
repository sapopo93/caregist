"""Bounded Postgres reads of original CQC evidence, pinned for payment retries."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from api.database import get_connection
from api.services.territory_brief import (
    PurchaseContext, generate_brief_from_rows, known_territories, validate_scope,
)
from api.services.cqc_freshness import FRESHNESS_SLA

MAX_SCOPE_LOCATIONS = 25000


class SourceUnavailable(OSError):
    """No complete, usable edition is available; do not take a payment."""


@asynccontextmanager
async def _source_connection(conn):
    if conn is not None:
        yield conn
    else:
        async with get_connection() as acquired:
            yield acquired


async def load_source(raw_scope, *, edition_id=None, connection=None):
    try:
        async with _source_connection(connection) as conn:
            async with conn.transaction():
                edition = await conn.fetchrow(
                    """SELECT * FROM territory_brief_source_editions
                       WHERE ($1::bigint IS NULL OR id = $1)
                       ORDER BY source_retrieved_at DESC, id DESC LIMIT 1""", edition_id,
                )
                if not edition:
                    raise SourceUnavailable("No CQC evidence edition has been imported")
                if edition_id is None:
                    age = datetime.now(timezone.utc) - edition["source_retrieved_at"]
                    if age.total_seconds() < 0 or age > FRESHNESS_SLA:
                        raise SourceUnavailable("CQC evidence edition is stale or future dated")
                count = await conn.fetchval(
                    "SELECT count(*) FROM territory_brief_source_locations WHERE edition_id = $1",
                    edition["id"],
                )
                if count != edition["location_count"]:
                    raise SourceUnavailable("CQC evidence edition is incomplete")
                territories = await conn.fetch(
                    """SELECT DISTINCT local_authority AS "localAuthority", region
                       FROM territory_brief_source_locations WHERE edition_id = $1
                       ORDER BY "localAuthority", region""", edition["id"],
                )
                scope = validate_scope(raw_scope, known_territories(territories))
                column = "local_authority" if scope.kind == "local_authority" else "region"
                rows = await conn.fetch(
                    f"""SELECT payload, provider_name, rule_rating_applies, rule_rating, rule_rating_date
                        FROM territory_brief_source_locations
                        WHERE edition_id = $1 AND lower({column}) = lower($2)
                        ORDER BY location_id LIMIT $3""",
                    edition["id"], scope.name, MAX_SCOPE_LOCATIONS + 1,
                )
                if not rows or len(rows) > MAX_SCOPE_LOCATIONS:
                    raise SourceUnavailable("Territory is empty or exceeds the generation bound")
    except (SourceUnavailable, ValueError):
        raise
    except Exception as exc:
        raise SourceUnavailable("Postgres CQC evidence is unavailable") from exc
    locations, names, ruled = [], {}, {}
    for row in rows:
        payload = row["payload"]
        payload = json.loads(payload) if isinstance(payload, str) else dict(payload)
        locations.append(payload)
        names[str(payload.get("providerId") or "").strip()] = row["provider_name"]
        if row["rule_rating_applies"]:
            ruled[str(payload.get("locationId") or "").strip()] = (row["rule_rating"], row["rule_rating_date"])
    # The rating rule's result frozen with the edition (migration 066).
    return scope, {**dict(edition), "rule_ratings": ruled}, locations, names


def build_brief(scope, edition, locations, names, context):
    label = f"postgres-cqc-edition-{edition['id']}"
    return generate_brief_from_rows(
        scope, context, location_rows=locations, provider_names=names,
        locations_label=f"{label}-locations-{edition['locations_sha256']}",
        providers_label=f"{label}-providers-{edition['providers_sha256']}",
        source_as_of=edition["source_as_of"],
        file_ratings=edition.get("rule_ratings") or None,
    )


async def prepare_checkout(raw_scope):
    scope, edition, locations, names = await load_source(raw_scope)
    brief = build_brief(scope, edition, locations, names, PurchaseContext(
        order_reference="checkout-preflight", generated_at=datetime.now(timezone.utc),
    ))
    if len(brief.shortlist) < scope.shortlist_target:
        raise SourceUnavailable("CQC evidence cannot supply the requested shortlist")
    return scope, edition["id"]
