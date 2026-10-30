"""Stripe-confirmed fulfilment of the GBP 745 Territory Opportunity Brief.

Called from the Stripe webhook (``checkout.session.completed`` /
``checkout.session.async_payment_succeeded``) after signature verification and
the shared event-dedup insert. It follows the same atomicity model as the
retired full-dataset handler (`_handle_dataset_checkout_completed`):

* all DB mutations run in the webhook's single transaction;
* a duplicate delivery of the same event does nothing (shared
  ``stripe_processed_events`` guard) and a re-run against an already-``fulfilled``
  order is an explicit no-op here too;
* if generation, upload, or an in-function persistence write fails after payment,
  the handler records the failure
  on a *separate* connection after rollback (so it cannot wait on its own lock) and re-raises,
  so Stripe re-delivers and the order is retried - it is never marked delivered.

The outer webhook commits after this function returns. A commit failure or
process interruption before the post-rollback recorder runs cannot carry this
in-memory context forward. Uploaded blobs can also remain orphaned after a later
database failure and require an external reconciliation/cleanup policy.

Generation and Blob upload are injected so this is fully testable without the
CQC snapshot, Stripe, or a network.
"""

from __future__ import annotations

import hashlib
import inspect
import html
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

logger = logging.getLogger("caregist.billing.territory_brief")

METADATA_TYPE = "territory_opportunity_brief"

# Product-specific immediate-supply consent. This is NOT the retired
# FULL_DATASET_CONSENT_TEXT: the Brief is a bespoke research pack sold under its
# own Business Terms. The exact wording used in production must be the
# solicitor-approved string whose SHA-256 is TERRITORY_BRIEF_CONSENT_SHA256; the
# default below is a placeholder and deliberately fails the config hash gate
# until it is replaced and approved.
TERRITORY_BRIEF_CONSENT_TEXT = (
    "I expressly request that CareGist begin preparing and supply my Territory Opportunity "
    "Brief immediately, before the end of the 14-day cancellation period. I understand and "
    "agree that once the completed Brief has been made available to download I lose my "
    "statutory right to cancel this purchase. This does not affect my rights if the Brief is "
    "faulty or not as described. I agree to the CareGist Business Terms of Service."
)

OGL_ATTRIBUTION = "Contains public sector information licensed under the Open Government Licence v3.0"

_MAX_GENERATION_ATTEMPTS = 5


class TerritoryBriefFulfilmentError(RuntimeError):
    """Raised for any state that must trigger a Stripe re-delivery."""


class TerritoryBriefGenerationError(TerritoryBriefFulfilmentError):
    """Carry a trusted failure recorder to the webhook's post-rollback boundary."""

    def __init__(self, order_id: str, message: str, recorder, context: dict[str, Any] | None = None):
        super().__init__(f"territory-brief generation failed for order {order_id}: {message}")
        self.order_id = order_id
        self.failure_message = message
        self.recorder = recorder
        self.context = context

    async def record_failure(self) -> None:
        if self.context is None:
            await self.recorder(self.order_id, self.failure_message)
            return
        await self.recorder(self.order_id, self.failure_message, self.context)


@dataclass(frozen=True)
class GeneratedPack:
    pdf_bytes: bytes
    csv_text: str
    scope_name: str
    considered: int
    shortlisted: int
    source_version: str | None = None
    provider_records: tuple[dict[str, Any], ...] = ()
    evidence: dict[str, Any] | None = None

    @property
    def sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.pdf_bytes)
        digest.update(self.csv_text.encode("utf-8"))
        return digest.hexdigest()


@dataclass(frozen=True)
class BlobRef:
    pathname: str


@dataclass(frozen=True)
class FulfilmentSettings:
    stripe_price_territory_brief: str
    terms_version: str
    terms_sha256: str
    consent_sha256: str
    app_url: str


@dataclass(frozen=True)
class FulfilmentDeps:
    """Injected side-effecting collaborators."""

    # (order_row) -> GeneratedPack
    generate: Callable[[dict[str, Any]], GeneratedPack | Awaitable[GeneratedPack]]
    # (order_id, kind 'pdf'|'csv', data, content_type) -> BlobRef
    upload: Callable[[str, str, bytes, str], BlobRef]
    # stripe.checkout.Session.retrieve equivalent: (session_id) -> dict
    retrieve_session: Callable[[str], dict[str, Any]]
    # best-effort failure recorder on a *fresh* connection (so the note survives
    # the webhook rollback). Run only AFTER rollback and connection release:
    # Restores the validated payment and consent context after rollback, then
    # records failed/refunded state and advances the capped attempt counter.
    record_failure: Callable[[str, str, dict[str, Any] | None], Awaitable[None]]
    # audit hook mirroring api.utils.audit.write_audit_log(**kwargs)
    write_audit_log: Callable[..., Awaitable[None]]
    generate_with_connection: Callable[..., Awaitable[GeneratedPack]] | None = None
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def new_download_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validated_payment_intent(value: Any) -> str:
    if hasattr(value, "get"):
        value = value.get("id")
    if not isinstance(value, str) or len(value.strip()) <= 3 or not value.strip().startswith("pi_"):
        raise TerritoryBriefFulfilmentError("territory-brief checkout has no valid authoritative payment intent")
    return value.strip()


def _stable_payment_time(order: Any, session: dict[str, Any], fallback: datetime) -> datetime:
    """Return durable payment evidence so retries preserve one selection hash."""
    paid_at = order["paid_at"]
    if isinstance(paid_at, datetime):
        return paid_at.astimezone(timezone.utc)
    created = session.get("created")
    if isinstance(created, (int, float)) and created > 0:
        return datetime.fromtimestamp(created, tz=timezone.utc)
    return fallback


def validate_existing_payment_evidence(
    order: dict[str, Any] | Any,
    context: dict[str, Any],
) -> None:
    """Reject any attempt to replace a durable order/payment binding."""
    expected = {
        "stripe_payment_intent_id": context["payment_intent"],
        "amount_total": context["amount_total"],
        "currency": context["currency"],
    }
    if any(order[field] not in (None, value) for field, value in expected.items()):
        raise TerritoryBriefFulfilmentError("territory-brief checkout conflicts with durable payment evidence")


async def validate_existing_consent_evidence(
    conn,
    order_id: str,
    context: dict[str, Any],
    *,
    required: bool = False,
) -> bool:
    """Validate append-only consent evidence rather than trusting a conflict no-op."""
    consent = await conn.fetchrow(
        """
        SELECT stripe_checkout_session_id, terms_version, terms_sha256,
               consent_text_sha256, immediate_supply_consented,
               cancellation_right_acknowledged, evidence_source
        FROM territory_brief_consents
        WHERE order_id = $1
        """,
        order_id,
    )
    if not consent:
        if required:
            raise TerritoryBriefFulfilmentError("territory-brief order is missing durable consent evidence")
        return False
    if (
        consent["stripe_checkout_session_id"] != context["stripe_checkout_session_id"]
        or consent["terms_version"] != context["terms_version"]
        or consent["terms_sha256"] != context["terms_sha256"]
        or consent["consent_text_sha256"] != context["consent_text_sha256"]
        or consent["immediate_supply_consented"] is not True
        or consent["cancellation_right_acknowledged"] is not True
        or consent["evidence_source"] != "stripe_checkout_terms_checkbox"
    ):
        raise TerritoryBriefFulfilmentError("territory-brief checkout conflicts with durable consent evidence")
    return True


def _row_value(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def build_checkout_metadata(
    order_id: str,
    scope: dict[str, Any],
    cfg: FulfilmentSettings,
    *,
    scope_ref: str | None = None,
) -> dict[str, str]:
    """Immutable metadata to attach to the Stripe Checkout Session.

    Fulfilment re-validates every value against the authoritative session and the
    local order, so this is a correlation aid, not a trust anchor.

    ``scope_ref`` is an opaque identifier of the private buyer scope. The rules
    themselves (objective, exclusions) are never put in Stripe metadata.
    """
    metadata = {
        "type": METADATA_TYPE,
        "order_id": str(order_id),
        "price_id": cfg.stripe_price_territory_brief,
        "scope_kind": str(scope["kind"]),
        "scope_name": str(scope["name"]),
        "scope_window_days": str(scope.get("window_days", 90)),
        "scope_shortlist_target": str(scope.get("shortlist_target", 30)),
        "terms_version": cfg.terms_version,
        "terms_sha256": cfg.terms_sha256,
        "consent_text_sha256": cfg.consent_sha256,
    }
    if scope_ref:
        metadata["scope_ref"] = str(scope_ref)
    return metadata


async def fulfil_territory_brief_order(
    conn,
    session: dict[str, Any],
    *,
    cfg: FulfilmentSettings,
    deps: FulfilmentDeps,
) -> None:
    session_id = session.get("id")
    if not session_id:
        raise TerritoryBriefFulfilmentError("territory-brief checkout missing session id")

    authoritative = deps.retrieve_session(session_id)
    metadata = authoritative.get("metadata", {}) or {}
    order_id = metadata.get("order_id")
    if metadata.get("type") != METADATA_TYPE or not order_id:
        raise TerritoryBriefFulfilmentError("territory-brief checkout missing immutable order metadata")
    if authoritative.get("payment_status") != "paid":
        raise TerritoryBriefFulfilmentError("territory-brief checkout completed before payment became valid")
    if authoritative.get("currency") != "gbp" or authoritative.get("amount_total") != 74500:
        raise TerritoryBriefFulfilmentError("territory-brief checkout must be paid at GBP 745.00")
    if (authoritative.get("consent", {}) or {}).get("terms_of_service") != "accepted":
        raise TerritoryBriefFulfilmentError("territory-brief checkout has no Stripe terms acceptance")

    if (
        metadata.get("terms_version") != cfg.terms_version
        or (metadata.get("terms_sha256") or "").lower() != cfg.terms_sha256.lower()
        or (metadata.get("consent_text_sha256") or "").lower() != cfg.consent_sha256.lower()
    ):
        raise TerritoryBriefFulfilmentError("territory-brief checkout legal evidence does not match approved terms")

    line_items = (authoritative.get("line_items", {}) or {}).get("data", [])
    actual = [((item.get("price", {}) or {}).get("id"), int(item.get("quantity") or 0)) for item in line_items]
    if actual != [(cfg.stripe_price_territory_brief, 1)]:
        raise TerritoryBriefFulfilmentError(f"territory-brief checkout has unexpected line items: {actual!r}")

    payment_intent = _validated_payment_intent(authoritative.get("payment_intent"))
    payment_evidence_at = deps.now()
    failure_context = {
        "payment_intent": payment_intent,
        "amount_total": authoritative["amount_total"],
        "currency": authoritative["currency"].lower(),
        "paid_at": payment_evidence_at,
        "stripe_checkout_session_id": session_id,
        "terms_version": cfg.terms_version,
        "terms_sha256": cfg.terms_sha256.lower(),
        "consent_text_sha256": cfg.consent_sha256.lower(),
        "accepted_at": payment_evidence_at,
    }

    # Refund and generation take the same transaction-scoped payment lock before
    # either touches the order. The durable audit check closes the gap where a
    # refund arrived after the generation transaction rolled back its payment row.
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended('caregist-payment:' || $1, 0))",
        payment_intent,
    )
    fully_refunded = await conn.fetchval(
        """
        SELECT EXISTS (
          SELECT 1
          FROM audit_log
          WHERE action = 'billing.charge.refund'
            AND metadata->>'payment_intent' = $1
            AND metadata->>'fully_refunded' = 'true'
        )
        """,
        payment_intent,
    )
    order = await conn.fetchrow(
        """
        SELECT id, customer_email, stripe_price_id, status,
               scope_kind, scope_name, scope_window_days, scope_shortlist_target,
               generation_attempts, stripe_payment_intent_id, amount_total, currency,
               (SELECT v.id::text FROM territory_brief_scope_versions v
                 WHERE v.order_id = territory_brief_orders.id AND v.version = 1) AS bound_scope_ref,
               source_edition_id, paid_at
        FROM territory_brief_orders
        WHERE id = $1 AND stripe_checkout_session_id = $2
        FOR UPDATE
        """,
        order_id,
        session_id,
    )
    if not order or order["stripe_price_id"] != cfg.stripe_price_territory_brief:
        raise TerritoryBriefFulfilmentError("territory-brief checkout does not match its reserved local order")
    if (
        metadata.get("scope_kind") != order["scope_kind"]
        or metadata.get("scope_name") != order["scope_name"]
        or metadata.get("scope_window_days") != str(order["scope_window_days"])
        or metadata.get("scope_shortlist_target") != str(order["scope_shortlist_target"])
        or metadata.get("price_id") != order["stripe_price_id"]
    ):
        raise TerritoryBriefFulfilmentError("territory-brief checkout scope does not match the reserved order")
    bound_scope_ref = _row_value(order, "bound_scope_ref")
    if (metadata.get("scope_ref") or None) != (bound_scope_ref or None):
        raise TerritoryBriefFulfilmentError("territory-brief checkout buyer-scope reference does not match the order")
    validate_existing_payment_evidence(order, failure_context)
    await validate_existing_consent_evidence(
        conn,
        str(order_id),
        failure_context,
        required=order["status"] == "fulfilled",
    )
    if fully_refunded:
        raise TerritoryBriefFulfilmentError("refunded territory-brief payment cannot be fulfilled")
    if order["status"] == "refunded":
        raise TerritoryBriefFulfilmentError("refunded territory-brief order cannot be fulfilled")
    if order["status"] == "fulfilled":
        logger.info("Territory-brief order %s already fulfilled - duplicate delivery ignored", order_id)
        return
    if int(order["generation_attempts"] or 0) >= _MAX_GENERATION_ATTEMPTS:
        raise TerritoryBriefFulfilmentError(
            f"territory-brief order {order_id} exceeded {_MAX_GENERATION_ATTEMPTS} generation attempts; needs manual review"
        )

    selection_confirmed_at = _stable_payment_time(order, authoritative, payment_evidence_at)
    failure_context["paid_at"] = selection_confirmed_at

    try:
        # generation_attempts is maintained by the post-rollback recorder. All
        # writes from payment binding through fulfilment audit are kept inside
        # this contextual boundary so a rollback can restore trusted evidence.
        await conn.execute(
            """
            UPDATE territory_brief_orders
            SET status = 'generating',
                stripe_payment_intent_id = COALESCE(stripe_payment_intent_id, $1),
                amount_total = COALESCE(amount_total, $2),
                currency = COALESCE(currency, LOWER($3)),
                paid_at = COALESCE(paid_at, NOW()),
                last_error = NULL,
                updated_at = NOW()
            WHERE id = $4
            """,
            payment_intent,
            authoritative.get("amount_total"),
            authoritative.get("currency"),
            order_id,
        )
        await conn.execute(
            """
            INSERT INTO territory_brief_consents (
              order_id, stripe_checkout_session_id, terms_version, terms_sha256,
              consent_text_sha256, immediate_supply_consented,
              cancellation_right_acknowledged, accepted_at, evidence_source
            ) VALUES ($1, $2, $3, $4, $5, TRUE, TRUE, $6,
                      'stripe_checkout_terms_checkbox')
            ON CONFLICT (order_id) DO NOTHING
            """,
            order_id,
            session_id,
            cfg.terms_version,
            cfg.terms_sha256.lower(),
            cfg.consent_sha256.lower(),
            failure_context["accepted_at"],
        )
        await validate_existing_consent_evidence(
            conn,
            str(order_id),
            failure_context,
            required=True,
        )
        generation_row = dict(order)
        if bound_scope_ref:
            from api.services.territory_brief_scope_store import load_scope_rules

            try:
                generation_row["scope_rules"] = await load_scope_rules(conn, bound_scope_ref, str(order_id))
            except LookupError as exc:
                raise TerritoryBriefFulfilmentError(str(exc)) from exc
        pack = (
            deps.generate_with_connection(generation_row, conn)
            if deps.generate_with_connection
            else deps.generate(generation_row)
        )
        if inspect.isawaitable(pack):
            pack = await pack
        from api.services import customer_package as packages

        customer_binding = hashlib.sha256(order["customer_email"].strip().lower().encode("utf-8")).hexdigest()
        providers = list(pack.provider_records)
        if not providers:
            providers = packages.provider_records_from_csv(
                pack.csv_text,
                provider_cap=int(order["scope_shortlist_target"]),
            )
        if len(providers) != pack.shortlisted:
            raise TerritoryBriefFulfilmentError(
                "generated shortlist does not match the distinct provider evidence used by the customer package"
            )
        snapshot = packages.verified_snapshot(
            order_reference=str(order_id),
            customer_reference=f"email-sha256:{customer_binding}",
            product_id="territory-opportunity-brief",
            payment_reference=payment_intent,
            template_version=packages.TERRITORY_TEMPLATE_VERSION,
            source_version=pack.source_version or f"postgres-cqc-edition-{order['source_edition_id']}",
            geography=pack.scope_name,
            rating_context_criteria=(
                f"{order['scope_window_days']}-day supported-signal window",
                f"up to {order['scope_shortlist_target']} distinct providers",
            ),
            provider_cap=int(order["scope_shortlist_target"]),
            buyer_objective="Territory opportunity prioritisation",
            confirmed_at=selection_confirmed_at,
        )
        customer_package = packages.build_package_bytes(
            snapshot,
            {
                "brief.pdf": packages.PackageArtifact("brief.pdf", pack.pdf_bytes, "application/pdf"),
                "providers.csv": packages.PackageArtifact(
                    "providers.csv", pack.csv_text.encode("utf-8"), "text/csv; charset=utf-8"
                ),
            },
            provider_records=providers,
            evidence=pack.evidence,
        )
        pdf_ref = deps.upload(order_id, "pdf", pack.pdf_bytes, "application/pdf")
        csv_ref = deps.upload(order_id, "csv", pack.csv_text.encode("utf-8"), "text/csv; charset=utf-8")
        zip_ref = deps.upload(order_id, "zip", customer_package.zip_bytes, "application/zip")

        await conn.execute(
            """
        UPDATE territory_brief_orders
        SET status = 'fulfilled',
            blob_pdf_pathname = $1,
            blob_csv_pathname = $2,
            artifact_sha256 = $3,
            blob_zip_pathname = $5,
            package_sha256 = $6,
            selection_snapshot = $7::jsonb,
            selection_sha256 = $8,
            package_manifest = $9::jsonb,
            package_version = $10,
            fulfilled_at = COALESCE(fulfilled_at, NOW()),
            updated_at = NOW()
        WHERE id = $4
        """,
            pdf_ref.pathname,
            csv_ref.pathname,
            pack.sha256,
            order_id,
            zip_ref.pathname,
            customer_package.sha256,
            json.dumps(customer_package.selection, sort_keys=True),
            snapshot.sha256,
            json.dumps(customer_package.manifest, sort_keys=True),
            customer_package.version,
        )

        if bound_scope_ref:
            from api.services.territory_brief_scope_store import schedule_exclusion_purge

            await schedule_exclusion_purge(conn, bound_scope_ref)

        raw_pdf, hash_pdf = new_download_token()
        raw_csv, hash_csv = new_download_token()
        raw_zip, hash_zip = new_download_token()
        for token_hash, kind in ((hash_pdf, "pdf"), (hash_csv, "csv"), (hash_zip, "zip")):
            await conn.execute(
                """
            INSERT INTO territory_brief_download_tokens (token_hash, order_id, artifact_kind, expires_at)
            VALUES ($1, $2, $3, NOW() + INTERVAL '30 days')
            ON CONFLICT (order_id, artifact_kind) DO NOTHING
            """,
                token_hash,
                order_id,
                kind,
            )

        pdf_url = html.escape(f"{cfg.app_url}/api/export?token={raw_pdf}", quote=True)
        csv_url = html.escape(f"{cfg.app_url}/api/export?token={raw_csv}", quote=True)
        zip_url = html.escape(f"{cfg.app_url}/api/export?token={raw_zip}", quote=True)
        safe_version = html.escape(cfg.terms_version)
        email_body = (
            f"<p>Your Territory Opportunity Brief for {html.escape(pack.scope_name)} is ready.</p>"
            f'<p><a href="{zip_url}">Download the complete customer package (ZIP)</a></p>'
            f'<p><a href="{pdf_url}">Download the brief only (PDF)</a> &nbsp;|&nbsp; '
            f'<a href="{csv_url}">Download the shortlist (CSV)</a></p>'
            f"<p>Each link works for 30 days and up to 5 downloads. The brief covers "
            f"{pack.considered} location(s) with a supported signal; "
            f"{pack.shortlisted} are ranked candidates marked Qualification incomplete.</p>"
            f"<p>You expressly requested immediate supply and acknowledged that your statutory right "
            f"to cancel would be lost once the completed Brief was made available (Business Terms "
            f"{safe_version}). This does not affect your rights if the Brief is faulty or not as "
            f"described.</p>"
            f"<p>{html.escape(OGL_ATTRIBUTION)}. "
            '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">View licence</a>.</p>'
        )
        await conn.execute(
            """
        INSERT INTO pending_emails (to_email, subject, html_body, idempotency_key)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
        """,
            order["customer_email"],
            "Your CareGist Territory Opportunity Brief is ready",
            email_body,
            f"territory-brief-delivery:{order_id}",
        )

        await deps.write_audit_log(
            action="billing.territory_brief.fulfil",
            outcome="success",
            actor={"type": "system", "name": "stripe"},
            target_type="territory_brief_order",
            target_id=str(order_id),
            metadata={
                "session_id": session_id,
                "scope": f"{order['scope_kind']}:{order['scope_name']}",
                "artifact_sha256": pack.sha256,
                "package_sha256": customer_package.sha256,
                "selection_sha256": snapshot.sha256,
                "package_version": customer_package.version,
                "shortlisted": pack.shortlisted,
            },
            conn=conn,
        )
    except Exception as exc:  # noqa: BLE001 - failure must be recorded + retried
        message = f"{type(exc).__name__}: {exc}"[:1000]
        logger.exception("Territory-brief generation or persistence failed for order %s", order_id)
        # The webhook must release its order/payment locks before using another
        # connection to persist this failure. Awaiting that write here deadlocks.
        raise TerritoryBriefGenerationError(str(order_id), message, deps.record_failure, failure_context) from exc
