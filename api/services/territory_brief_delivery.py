"""Runtime wiring between the billing webhook and the Territory Opportunity Brief.

`api/services/territory_brief_fulfilment.py` is deliberately pure: generation,
Blob upload, Stripe retrieval and the failure recorder are all injected. This
module supplies those concrete collaborators, plus the two things the checkout
route needs before it can take a payment: the approved-terms evidence and the
live territory allow-list.

Everything here is inert until `settings.territory_self_serve_checkout_enabled`
is true. `Settings.validate_production()` hard-fails startup unless the approved
`TERRITORY_BRIEF_*` hashes, `STRIPE_PRICE_TERRITORY_BRIEF`, `BLOB_READ_WRITE_TOKEN`
and `RESEND_API_KEY` are all set, and `terms_evidence()` raises 503 until the
placeholder consent wording is replaced with the solicitor-approved string whose
SHA-256 matches `TERRITORY_BRIEF_CONSENT_SHA256`.

§5 (pre-enable engineering task): `_snapshot_rows()` reads the mirrored CQC
NDJSON snapshot, exactly as `tools/generate_radar_territory_sample.py` does.
That file is ~734 MB and is not in the serverless bundle, so generation MUST be
repointed at canonical Postgres (or a per-edition territory index) before the
feature flag is enabled. This module is the single seam for that change:
`_snapshot_rows()`, `scope_catalogue()` and `generate_pack()` are the only
places that touch the row source.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import stripe
from fastapi import HTTPException

from api.config import settings
from api.services.territory_brief_fulfilment import (
    TERRITORY_BRIEF_CONSENT_TEXT,
    BlobRef,
    FulfilmentDeps,
    FulfilmentSettings,
    GeneratedPack,
)

logger = logging.getLogger("caregist.billing.territory_brief")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCATIONS_SNAPSHOT = _REPO_ROOT / "_locations_detail.ndjson"
_PROVIDERS_SNAPSHOT = _REPO_ROOT / "_providers_detail.ndjson"

_HEX = frozenset("0123456789abcdef")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in _HEX for c in value)


def terms_evidence() -> tuple[str, str, str]:
    """(terms_version, terms_sha256, consent_text_sha256), or raise 503.

    Mirrors ``billing._dataset_terms``: the checkout route and the webhook must
    agree on exactly which published Business Terms and which immediate-supply
    consent wording the buyer accepted, and that evidence is re-checked at
    fulfilment against the values echoed in immutable Stripe metadata.
    """
    version = (settings.territory_brief_terms_version or "").strip()
    terms_sha = (settings.territory_brief_terms_sha256 or "").strip().lower()
    consent_sha = (settings.territory_brief_consent_sha256 or "").strip().lower()
    if not version or not _is_sha256(terms_sha) or not _is_sha256(consent_sha):
        raise HTTPException(
            status_code=503,
            detail="Territory Opportunity Brief checkout is awaiting approved Business Terms and consent wording.",
        )
    computed = hashlib.sha256(TERRITORY_BRIEF_CONSENT_TEXT.encode("utf-8")).hexdigest()
    if consent_sha != computed:
        # The wording shipped in territory_brief_fulfilment.TERRITORY_BRIEF_CONSENT_TEXT
        # is still the placeholder (or does not match the approved hash).
        raise HTTPException(
            status_code=503,
            detail="Territory Opportunity Brief consent wording does not match the approved hash.",
        )
    return version, terms_sha, consent_sha


def fulfilment_settings() -> FulfilmentSettings:
    version, terms_sha, consent_sha = terms_evidence()
    return FulfilmentSettings(
        stripe_price_territory_brief=settings.stripe_price_territory_brief,
        terms_version=version,
        terms_sha256=terms_sha,
        consent_sha256=consent_sha,
        app_url=settings.app_url,
    )


# --------------------------------------------------------------------------- #
# Row source (§5 seam)
# --------------------------------------------------------------------------- #


def _snapshot_paths() -> tuple[Path, Path]:
    if not _LOCATIONS_SNAPSHOT.exists() or not _PROVIDERS_SNAPSHOT.exists():
        raise FileNotFoundError(
            "CQC snapshot not available to the Territory Opportunity Brief generator. "
            "Before enabling TERRITORY_SELF_SERVE_CHECKOUT_ENABLED the generation source "
            "must be repointed at canonical Postgres (see "
            "docs/territory-brief-instant-delivery-2026-09-09.md §5)."
        )
    return _LOCATIONS_SNAPSHOT, _PROVIDERS_SNAPSHOT


@lru_cache(maxsize=1)
def scope_catalogue() -> dict[str, dict[str, str]]:
    """Normalised -> canonical name for every LA and region in the source data.

    Cached for the process lifetime: the set of English local authorities and
    regions is effectively static between snapshot refreshes. §5 replaces this
    with a Postgres-backed lookup.
    """
    from tools.generate_radar_territory_sample import _load_ndjson

    from api.services.territory_brief import known_territories

    locations_path, _ = _snapshot_paths()
    return known_territories(_load_ndjson(locations_path))


# --------------------------------------------------------------------------- #
# Injected collaborators
# --------------------------------------------------------------------------- #


def generate_pack(order_row: dict[str, Any]) -> GeneratedPack:
    """Generate the brief for a paid order and return the uploadable pack.

    ``order_row`` is the ``territory_brief_orders`` row selected FOR UPDATE in
    the webhook transaction. Scope is re-validated against live source data here
    (never trusting the stored value blindly); an unknown scope raises and the
    order is recorded failed + retried, never fulfilled.
    """
    from api.services.territory_brief import (
        PurchaseContext,
        brief_to_csv,
        generate_territory_opportunity_brief,
    )
    from api.services.territory_brief_render import render_brief_pdf

    locations_path, providers_path = _snapshot_paths()
    scope = {
        "kind": order_row["scope_kind"],
        "name": order_row["scope_name"],
        "window_days": int(order_row["scope_window_days"]),
        "shortlist_target": int(order_row["scope_shortlist_target"]),
    }
    context = PurchaseContext(
        order_reference=str(order_row["id"]),
        generated_at=datetime.now(timezone.utc),
        terms_version=(settings.territory_brief_terms_version or "").strip() or None,
    )
    brief = generate_territory_opportunity_brief(
        scope,
        context,
        locations_source=locations_path,
        providers_source=providers_path,
    )
    return GeneratedPack(
        pdf_bytes=render_brief_pdf(brief),
        csv_text=brief_to_csv(brief),
        scope_name=brief.scope.name,
        considered=brief.considered_locations,
        shortlisted=len(brief.shortlist),
    )


def upload_pack(order_id: str, kind: str, data: bytes, content_type: str) -> BlobRef:
    from api.services.blob_upload import put_blob

    pathname = f"territory-briefs/{order_id}/{secrets.token_hex(16)}/brief.{kind}"
    obj = put_blob(
        pathname,
        data,
        content_type=content_type,
        token=settings.blob_read_write_token,
    )
    return BlobRef(pathname=obj.pathname)


async def _record_failure(order_id: str, message: str) -> None:
    """Persist a generation failure on a fresh connection so it survives the
    webhook transaction rollback, and advance the attempt counter the next
    retry reads for its cap."""
    from api.database import get_connection

    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE territory_brief_orders
            SET status = 'failed',
                last_error = $2,
                generation_attempts = generation_attempts + 1,
                updated_at = NOW()
            WHERE id = $1 AND status NOT IN ('fulfilled', 'refunded')
            """,
            order_id,
            message,
        )


def _retrieve_session(session_id: str) -> dict[str, Any]:
    return stripe.checkout.Session.retrieve(session_id, expand=["line_items"])


def fulfilment_deps() -> FulfilmentDeps:
    from api.utils.audit import write_audit_log

    return FulfilmentDeps(
        generate=generate_pack,
        upload=upload_pack,
        retrieve_session=_retrieve_session,
        record_failure=_record_failure,
        write_audit_log=write_audit_log,
    )


def validate_checkout_price() -> None:
    """Check the configured Stripe object before reserving an order or taking money."""
    try:
        price = stripe.Price.retrieve(settings.stripe_price_territory_brief, expand=["product"])
    except stripe.StripeError as exc:
        raise HTTPException(status_code=503, detail="Territory Brief price verification is unavailable.") from exc
    product = price.get("product") or {}
    if not (
        price.get("id") == settings.stripe_price_territory_brief
        and price.get("active") is True
        and price.get("livemode") is settings.stripe_secret_key.startswith("sk_live_")
        and price.get("currency") == "gbp"
        and price.get("unit_amount") == 74500
        and price.get("type") == "one_time"
        and price.get("recurring") is None
        and price.get("lookup_key") == "territory_opportunity_brief_gbp_oneoff_v2"
        and hasattr(product, "get")
        and product.get("active") is True
    ):
        raise HTTPException(status_code=503, detail="Territory Brief price does not match the GBP 745 catalogue.")
