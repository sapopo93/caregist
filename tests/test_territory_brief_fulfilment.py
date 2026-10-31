"""Unit tests for Stripe-confirmed Territory Opportunity Brief fulfilment.

No database, Stripe, CQC snapshot or network: the connection is a recording
fake and every collaborator is injected.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from api.services import territory_brief_fulfilment as fulfil
from api.services.territory_brief_fulfilment import (
    FulfilmentDeps,
    FulfilmentSettings,
    GeneratedPack,
    TerritoryBriefFulfilmentError,
    build_checkout_metadata,
    fulfil_territory_brief_order,
)
from tests import package_fixtures

TERMS_SHA = "a" * 64
CONSENT_SHA = "b" * 64
PRICE = "price_territory_brief_test"

CFG = FulfilmentSettings(
    stripe_price_territory_brief=PRICE,
    terms_version="business-terms-2.2",
    terms_sha256=TERMS_SHA,
    consent_sha256=CONSENT_SHA,
    app_url="https://www.caregist.co.uk",
)

ORDER_ID = "11111111-1111-1111-1111-111111111111"


class FakeConn:
    def __init__(self, order_row, *, fully_refunded=False, consent_row=None, fail_sql=None):
        self._order_row = order_row
        self._fully_refunded = fully_refunded
        self._consent_row = consent_row
        self._fail_sql = fail_sql
        self.execches: list[tuple] = []
        self.calls: list[tuple] = []

    async def fetchrow(self, *args):
        self.calls.append(("fetchrow", *args))
        if "FROM territory_brief_consents" in args[0]:
            return self._consent_row
        return self._order_row

    async def fetchval(self, *args):
        self.calls.append(("fetchval", *args))
        return self._fully_refunded

    async def execute(self, *args):
        self.execches.append(args)
        self.calls.append(("execute", *args))
        if self._fail_sql and self._fail_sql in args[0]:
            raise RuntimeError("synthetic database write failure")
        if "INSERT INTO territory_brief_consents" in args[0] and self._consent_row is None:
            self._consent_row = _consent(
                stripe_checkout_session_id=args[2],
                terms_version=args[3],
                terms_sha256=args[4],
                consent_text_sha256=args[5],
            )
        return "UPDATE 1"

    def sql_log(self) -> str:
        return "\n".join(call[0] for call in self.execches)


def _order(**over):
    row = {
        "id": ORDER_ID,
        "customer_email": "buyer@example.com",
        "stripe_price_id": PRICE,
        "status": "pending",
        "scope_kind": "local_authority",
        "scope_name": "Southampton",
        "scope_window_days": 90,
        "scope_shortlist_target": 30,
        "generation_attempts": 0,
        "stripe_checkout_session_id": "cs_test_123",
        "stripe_payment_intent_id": None,
        "amount_total": None,
        "currency": None,
        "paid_at": None,
    }
    row.update(over)
    return row


def _consent(**over):
    row = {
        "stripe_checkout_session_id": "cs_test_123",
        "terms_version": "business-terms-2.2",
        "terms_sha256": TERMS_SHA,
        "consent_text_sha256": CONSENT_SHA,
        "immediate_supply_consented": True,
        "cancellation_right_acknowledged": True,
        "evidence_source": "stripe_checkout_terms_checkbox",
    }
    row.update(over)
    return row


def _session(**over):
    meta = {
        "type": fulfil.METADATA_TYPE,
        "order_id": ORDER_ID,
        "price_id": PRICE,
        "scope_kind": "local_authority",
        "scope_name": "Southampton",
        "scope_window_days": "90",
        "scope_shortlist_target": "30",
        "terms_version": "business-terms-2.2",
        "terms_sha256": TERMS_SHA,
        "consent_text_sha256": CONSENT_SHA,
    }
    meta.update(over.pop("metadata", {}))
    base = {
        "id": "cs_test_123",
        "metadata": meta,
        "payment_status": "paid",
        "consent": {"terms_of_service": "accepted"},
        "line_items": {"data": [{"price": {"id": PRICE}, "quantity": 1}]},
        "payment_intent": "pi_test_123",
        "amount_total": 74500,
        "currency": "gbp",
        "created": 1_761_800_000,
    }
    base.update(over)
    return base


def test_selection_confirmation_time_is_stable_across_retries() -> None:
    session = _session(created=1_700_000_000)
    first = fulfil._stable_payment_time(_order(), session)
    retry = fulfil._stable_payment_time(_order(), session)
    assert first == retry == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)

    persisted = datetime(2026, 10, 29, 9, tzinfo=timezone.utc)
    assert fulfil._stable_payment_time(_order(paid_at=persisted), session) == persisted
    with pytest.raises(TerritoryBriefFulfilmentError, match="no durable timestamp"):
        fulfil._stable_payment_time(_order(), _session(created=None))


def _deps(*, session=None, generate=None, fail_uploads=False, fail_upload_kind=None, failures=None, audits=None):
    failures = failures if failures is not None else []
    audits = audits if audits is not None else []

    def _generate(order_row):
        if generate == "raise":
            raise RuntimeError("boom in generator")
        if callable(generate):
            return generate(order_row)
        return GeneratedPack(
            pdf_bytes=package_fixtures.brief_pdf(order_row["id"], package_fixtures.roster(30, width=2)),
            csv_text="provider_id,location_id,organisation_name\n"
            + "".join(f"P{index:02d},L{index:02d},Provider {index}\n" for index in range(30)),
            scope_name=order_row["scope_name"],
            considered=38,
            shortlisted=30,
            source_version="test-edition-1",
            provider_records=tuple(
                {
                    "provider_id": f"P{index:02d}",
                    "provider_name": f"Provider {index}",
                    "location_ids": [f"L{index:02d}"],
                    "qualification_status": "Qualification incomplete",
                }
                for index in range(30)
            ),
        )

    def _upload(order_id, kind, data, content_type):
        if fail_uploads or kind == fail_upload_kind:
            raise RuntimeError("blob down")
        return fulfil.BlobRef(pathname=f"territory-briefs/{order_id}/xyz/brief.{kind}")

    async def _record_failure(order_id, message, context=None):
        failures.append((order_id, message, context))

    async def _audit(**kwargs):
        audits.append(kwargs)

    return FulfilmentDeps(
        generate=_generate,
        upload=_upload,
        retrieve_session=lambda sid: session or _session(),
        record_failure=_record_failure,
        write_audit_log=_audit,
    )


@pytest.mark.asyncio
async def test_happy_path_generates_uploads_entitles_and_emails():
    conn = FakeConn(_order())
    failures, audits = [], []
    deps = _deps(failures=failures, audits=audits)

    await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)

    sql = conn.sql_log()
    assert "SET status = 'generating'" in sql
    assert "INSERT INTO territory_brief_consents" in sql
    assert "SET status = 'fulfilled'" in sql
    token_inserts = [c for c in conn.execches if "territory_brief_download_tokens" in c[0]]
    assert len(token_inserts) == 3
    assert {c[3] for c in token_inserts} == {"pdf", "csv", "zip"}
    email_insert = next(c for c in conn.execches if "INSERT INTO pending_emails" in c[0])
    assert "Southampton" in email_insert[3]
    assert email_insert[4] == f"territory-brief-delivery:{ORDER_ID}"
    assert "/api/export?token=" in email_insert[3]
    assert not failures
    assert audits and audits[0]["action"] == "billing.territory_brief.fulfil"
    lock_index = next(i for i, call in enumerate(conn.calls) if "pg_advisory_xact_lock" in call[1])
    order_index = next(i for i, call in enumerate(conn.calls) if call[0] == "fetchrow")
    assert lock_index < order_index


@pytest.mark.asyncio
async def test_duplicate_delivery_on_fulfilled_order_is_a_noop():
    conn = FakeConn(
        _order(
            status="fulfilled",
            stripe_payment_intent_id="pi_test_123",
            amount_total=74500,
            currency="gbp",
        ),
        consent_row=_consent(),
    )
    deps = _deps()
    await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert len(conn.execches) == 1  # payment lock only; no order or delivery mutation
    assert "pg_advisory_xact_lock" in conn.execches[0][0]


@pytest.mark.asyncio
async def test_generation_failure_records_failure_and_reraises_without_fulfilling():
    conn = FakeConn(_order())
    failures = []
    deps = _deps(generate="raise", failures=failures)
    with pytest.raises(fulfil.TerritoryBriefGenerationError, match="generation failed") as error:
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert failures == []  # must wait for the webhook transaction to roll back
    await error.value.record_failure()
    sql = conn.sql_log()
    assert "SET status = 'generating'" in sql
    assert "SET status = 'fulfilled'" not in sql
    assert failures and failures[0][0] == ORDER_ID
    assert "boom in generator" in failures[0][1]
    assert failures[0][2]["payment_intent"] == "pi_test_123"
    assert failures[0][2]["amount_total"] == 74500
    assert failures[0][2]["currency"] == "gbp"
    assert failures[0][2]["terms_sha256"] == TERMS_SHA
    assert failures[0][2]["consent_text_sha256"] == CONSENT_SHA


@pytest.mark.asyncio
async def test_blob_upload_failure_is_treated_as_retryable_failure():
    conn = FakeConn(_order())
    failures = []
    deps = _deps(fail_uploads=True, failures=failures)
    with pytest.raises(fulfil.TerritoryBriefGenerationError) as error:
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert failures == []
    await error.value.record_failure()
    assert "SET status = 'fulfilled'" not in conn.sql_log()
    assert failures


@pytest.mark.asyncio
async def test_duplicate_provider_in_generated_final_list_never_uploads_or_fulfils():
    duplicate = {
        "provider_id": "P1",
        "provider_name": "Provider One",
        "location_ids": ["L1"],
        "qualification_status": "Qualification incomplete",
    }
    pack = GeneratedPack(
        package_fixtures.brief_pdf(ORDER_ID, [duplicate]),
        "provider_id,location_id,organisation_name\nP1,L1,Provider One\n",
        "Southampton",
        2,
        2,
        source_version="test-edition",
        provider_records=(duplicate, duplicate),
    )
    conn = FakeConn(_order())
    uploads: list[str] = []
    deps = _deps(generate=lambda _order: pack)
    deps = FulfilmentDeps(
        **{
            **deps.__dict__,
            "upload": lambda _order, kind, _data, _content_type: uploads.append(kind),
        }
    )

    with pytest.raises(fulfil.TerritoryBriefGenerationError, match="duplicate provider"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)

    assert uploads == []
    assert "SET status = 'fulfilled'" not in conn.sql_log()


@pytest.mark.asyncio
async def test_zip_upload_failure_never_fulfils_or_emails() -> None:
    conn = FakeConn(_order())

    with pytest.raises(fulfil.TerritoryBriefGenerationError, match="blob down"):
        await fulfil_territory_brief_order(
            conn,
            {"id": "cs_test_123"},
            cfg=CFG,
            deps=_deps(fail_upload_kind="zip"),
        )

    assert "SET status = 'fulfilled'" not in conn.sql_log()
    assert "INSERT INTO pending_emails" not in conn.sql_log()


@pytest.mark.asyncio
async def test_exhausted_attempts_stop_retrying():
    conn = FakeConn(_order(generation_attempts=5))
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="manual review"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_intent", [None, "", "pi_", "ch_wrong", {"id": ""}])
async def test_missing_or_invalid_authoritative_payment_intent_fails_before_generation(payment_intent):
    generated = []

    def generate(_order):
        generated.append(True)

    conn = FakeConn(_order())
    deps = _deps(session=_session(payment_intent=payment_intent), generate=generate)
    with pytest.raises(TerritoryBriefFulfilmentError, match="valid authoritative payment intent"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert not generated
    assert not conn.calls


@pytest.mark.asyncio
async def test_durable_full_refund_audit_fails_closed_before_order_or_generation():
    conn = FakeConn(_order(), fully_refunded=True)
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="refunded"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert any(call[0] == "fetchrow" for call in conn.calls)
    assert "SET status = 'generating'" not in conn.sql_log()


@pytest.mark.asyncio
async def test_conflicting_existing_payment_identity_fails_before_generation():
    generated = []
    conn = FakeConn(_order(status="failed", stripe_payment_intent_id="pi_other"))
    deps = _deps(generate=lambda _order: generated.append(True))
    with pytest.raises(TerritoryBriefFulfilmentError, match="durable payment evidence"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert not generated
    assert "SET status = 'generating'" not in conn.sql_log()


@pytest.mark.asyncio
async def test_conflicting_existing_consent_fails_before_generation_even_for_duplicate():
    generated = []
    conn = FakeConn(
        _order(
            status="fulfilled",
            stripe_payment_intent_id="pi_test_123",
            amount_total=74500,
            currency="gbp",
        ),
        consent_row=_consent(terms_version="other-version"),
    )
    deps = _deps(generate=lambda _order: generated.append(True))
    with pytest.raises(TerritoryBriefFulfilmentError, match="durable consent evidence"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert not generated
    assert "SET status = 'generating'" not in conn.sql_log()


@pytest.mark.asyncio
async def test_database_failure_after_both_uploads_carries_recovery_context():
    failures = []
    uploads = []
    conn = FakeConn(_order(), fail_sql="SET status = 'fulfilled'")
    deps = _deps(failures=failures)

    original_upload = deps.upload

    def recording_upload(*args):
        uploads.append(args[1])
        return original_upload(*args)

    deps = fulfil.FulfilmentDeps(
        generate=deps.generate,
        upload=recording_upload,
        retrieve_session=deps.retrieve_session,
        record_failure=deps.record_failure,
        write_audit_log=deps.write_audit_log,
    )
    with pytest.raises(fulfil.TerritoryBriefGenerationError) as error:
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert uploads == ["pdf", "csv", "zip"]
    await error.value.record_failure()
    assert failures[0][2]["payment_intent"] == "pi_test_123"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "session_over, match",
    [
        ({"payment_status": "no_payment_required"}, "before payment became valid"),
        ({"amount_total": 79500}, "GBP 745"),
        ({"amount_total": 0}, "GBP 745"),
        ({"currency": "usd"}, "GBP 745"),
        ({"metadata": {"scope_window_days": "365"}}, "scope does not match"),
        ({"metadata": {"scope_shortlist_target": "50"}}, "scope does not match"),
        ({"metadata": {"price_id": "price_other"}}, "scope does not match"),
        ({"payment_status": "unpaid"}, "before payment became valid"),
        ({"consent": {}}, "no Stripe terms acceptance"),
        ({"metadata": {"type": "full_dataset"}}, "immutable order metadata"),
        ({"metadata": {"terms_sha256": "c" * 64}}, "legal evidence does not match"),
        ({"metadata": {"consent_text_sha256": "d" * 64}}, "legal evidence does not match"),
        ({"line_items": {"data": [{"price": {"id": "price_other"}, "quantity": 1}]}}, "unexpected line items"),
        ({"line_items": {"data": [{"price": {"id": PRICE}, "quantity": 2}]}}, "unexpected line items"),
        ({"metadata": {"scope_name": "Kent"}}, "scope does not match"),
    ],
)
async def test_rejects_tampered_or_wrong_product_events(session_over, match):
    conn = FakeConn(_order())
    deps = _deps(session=_session(**session_over))
    with pytest.raises(TerritoryBriefFulfilmentError, match=match):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert "SET status = 'fulfilled'" not in conn.sql_log()


@pytest.mark.asyncio
async def test_refunded_order_cannot_be_fulfilled():
    conn = FakeConn(_order(status="refunded"))
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="refunded"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


@pytest.mark.asyncio
async def test_order_not_matching_reserved_row_is_rejected():
    conn = FakeConn(_order(stripe_price_id="price_wrong"))
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="does not match its reserved local order"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


def test_generated_pack_sha_is_stable_and_content_bound():
    a = GeneratedPack(b"pdf-a", "csv-a", "X", 1, 1)
    b = GeneratedPack(b"pdf-a", "csv-a", "X", 1, 1)
    c = GeneratedPack(b"pdf-a", "csv-DIFFERENT", "X", 1, 1)
    assert a.sha256 == b.sha256 != c.sha256
    assert a.sha256 == hashlib.sha256(b"pdf-a" + b"csv-a").hexdigest()


def test_build_checkout_metadata_is_flat_strings():
    meta = build_checkout_metadata(ORDER_ID, {"kind": "region", "name": "South East"}, CFG)
    assert meta["type"] == fulfil.METADATA_TYPE
    assert all(isinstance(v, str) for v in meta.values())
    assert meta["terms_sha256"] == TERMS_SHA


@pytest.mark.asyncio
async def test_package_retains_bound_objective_and_exclusion_hashes_without_ids(monkeypatch):
    import json
    from api.services import territory_brief_scope_store as store
    rules = {"scope_ref": "scope-test", "rule_version": 3,
             "buyer_objective": "Assess compliance implementation support",
             "excluded_provider_ids": ["1-SECRET-EXCLUSION"], "excluded_location_ids": ["1-PRIVATE-LOCATION"]}

    async def load(*args):
        return rules

    async def purge(*args):
        pass

    monkeypatch.setattr(store, "load_scope_rules", load)
    monkeypatch.setattr(store, "schedule_exclusion_purge", purge)
    conn = FakeConn(_order(bound_scope_ref="scope-test"))
    await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG,
        deps=_deps(session=_session(metadata={"scope_ref": "scope-test"})))
    write = next(c for c in conn.execches if "selection_snapshot = $7" in c[0])
    snapshot = json.loads(write[7])
    assert snapshot["buyer_objective"] == rules["buyer_objective"]
    retained = json.loads(snapshot["scope_rules_json"])
    assert retained["rule_version"] == 3
    assert retained["excluded_provider_count"] == retained["excluded_location_count"] == 1
    assert "1-SECRET-EXCLUSION" not in write[7] and "1-PRIVATE-LOCATION" not in write[7]
    assert len(retained["excluded_provider_sha256"]) == 64
