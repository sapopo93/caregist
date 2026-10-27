"""Private versioned buyer scope: storage, Stripe-metadata boundary, fulfilment binding, retention.

No database or network. A small in-memory fake stands in for asyncpg; the real
schema is exercised by tests/test_territory_brief_scope_pg.py when a Postgres is
available.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from api.routers import billing
from api.services import territory_brief_fulfilment as fulfil
from api.services import territory_brief_scope_store as store
from api.services.territory_brief import TerritoryScope, validate_scope
from tests.test_billing_territory_brief_checkout import CATALOGUE, _Conn as _BillingConn, brief_settings  # noqa: F401
from tests.test_territory_brief_fulfilment import (
    CFG,
    ORDER_ID,
    FakeConn,
    _deps,
    _order,
    _session,
)

OBJECTIVE = "Governance support for West Midlands domiciliary care providers"
RULES = TerritoryScope(
    kind="local_authority",
    name="Southampton",
    buyer_objective=OBJECTIVE,
    excluded_provider_ids=("1-100000001", "1-100000002"),
    excluded_location_ids=("1-200000001",),
)
SCOPE_REF = "22222222-2222-2222-2222-222222222222"


class StoreConn:
    """Records writes and serves them back, like the two scope tables."""

    def __init__(self):
        self.versions: dict[str, dict] = {}
        self.exclusions: list[tuple[str, str, str]] = []
        self.writes: list[str] = []

    async def fetchrow(self, sql, *args):
        if "INSERT INTO territory_brief_scope_versions" in sql:
            self.versions[SCOPE_REF] = {
                "id": SCOPE_REF,
                "order_id": args[0],
                "rule_version": args[3],
                "buyer_objective": args[4],
                "provider_exclusion_count": args[5],
                "location_exclusion_count": args[6],
                "scope_sha256": args[7],
                "exclusions_purged_at": None,
            }
            return {"id": SCOPE_REF}
        if "FROM territory_brief_scope_versions" in sql:
            row = self.versions.get(args[0])
            return row if row and row["order_id"] == args[1] else None
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        return [{"id_kind": k, "cqc_id": c} for sid, k, c in self.exclusions if sid == args[0]]

    async def execute(self, sql, *args):
        self.writes.append(sql)
        if "INSERT INTO territory_brief_scope_exclusions" in sql:
            self.exclusions.append((args[0], args[1], args[2]))
        return "OK"


@pytest.mark.asyncio
async def test_store_and_load_round_trip_and_hash_is_order_independent():
    conn = StoreConn()
    ref = await store.insert_scope_version(conn, ORDER_ID, RULES)
    assert ref == SCOPE_REF
    loaded = await store.load_scope_rules(conn, ref, ORDER_ID)
    assert loaded["buyer_objective"] == OBJECTIVE
    assert loaded["excluded_provider_ids"] == ["1-100000001", "1-100000002"]
    assert loaded["excluded_location_ids"] == ["1-200000001"]
    shuffled = TerritoryScope(
        kind="local_authority",
        name="Southampton",
        buyer_objective=OBJECTIVE,
        excluded_provider_ids=("1-100000002", "1-100000001"),
        excluded_location_ids=("1-200000001",),
    )
    assert store.scope_rules_sha256(shuffled) == store.scope_rules_sha256(RULES)


@pytest.mark.asyncio
async def test_scope_without_rules_is_not_stored():
    with pytest.raises(ValueError):
        await store.insert_scope_version(StoreConn(), ORDER_ID, TerritoryScope(kind="region", name="South East"))


@pytest.mark.asyncio
async def test_reference_from_another_order_is_refused():
    conn = StoreConn()
    ref = await store.insert_scope_version(conn, ORDER_ID, RULES)
    with pytest.raises(LookupError):
        await store.load_scope_rules(conn, ref, "99999999-9999-9999-9999-999999999999")


@pytest.mark.asyncio
async def test_purged_or_incomplete_exclusions_block_regeneration():
    conn = StoreConn()
    ref = await store.insert_scope_version(conn, ORDER_ID, RULES)
    conn.exclusions.pop()  # list no longer complete
    with pytest.raises(LookupError, match="no longer complete"):
        await store.load_scope_rules(conn, ref, ORDER_ID)
    conn2 = StoreConn()
    ref2 = await store.insert_scope_version(conn2, ORDER_ID, RULES)
    conn2.versions[ref2]["exclusions_purged_at"] = datetime.now(timezone.utc)
    with pytest.raises(LookupError):
        await store.load_scope_rules(conn2, ref2, ORDER_ID)


def test_stripe_metadata_carries_only_the_opaque_reference():
    meta = fulfil.build_checkout_metadata(
        ORDER_ID, {"kind": "local_authority", "name": "Southampton"}, CFG, scope_ref=SCOPE_REF
    )
    assert meta["scope_ref"] == SCOPE_REF
    blob = " ".join(meta.values())
    assert OBJECTIVE not in blob and "1-100000001" not in blob and "1-200000001" not in blob
    legacy = fulfil.build_checkout_metadata(ORDER_ID, {"kind": "region", "name": "South East"}, CFG)
    assert "scope_ref" not in legacy


@pytest.mark.asyncio
async def test_checkout_with_rules_stores_privately_and_sends_only_the_reference(monkeypatch, brief_settings):  # noqa: F811
    conn = _BillingConn()
    inserted = []

    async def fake_insert(c, order_id, scope, **kw):
        inserted.append(scope)
        return SCOPE_REF

    monkeypatch.setattr(store, "insert_scope_version", fake_insert)

    @asynccontextmanager
    async def fake_get_connection():
        yield conn

    monkeypatch.setattr(billing, "get_connection", fake_get_connection)
    create = Mock(return_value=Mock(url="https://checkout.stripe.com/c/pay/cs_x", id="cs_x"))
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    request = billing.TerritoryBriefCheckoutRequest(
        email="buyer@example.com",
        scope_kind="local_authority",
        scope_name="southampton",
        buyer_objective=OBJECTIVE,
        excluded_provider_ids=["1-100000001"],
    )
    result = await billing.create_territory_brief_checkout(request)

    assert inserted and inserted[0].excluded_provider_ids == ("1-100000001",)
    metadata = create.call_args.kwargs["metadata"]
    assert metadata["scope_ref"] == SCOPE_REF
    assert OBJECTIVE not in " ".join(metadata.values()) and "1-100000001" not in " ".join(metadata.values())
    assert OBJECTIVE not in str(result) and "1-100000001" not in str(result)


@pytest.mark.asyncio
async def test_checkout_rejects_names_as_exclusions(monkeypatch, brief_settings):  # noqa: F811
    monkeypatch.setattr(billing, "get_connection", Mock())
    request = billing.TerritoryBriefCheckoutRequest(
        email="buyer@example.com",
        scope_kind="local_authority",
        scope_name="southampton",
        excluded_provider_ids=["Acme Care Ltd"],
    )
    with pytest.raises(billing.HTTPException) as err:
        await billing.create_territory_brief_checkout(request)
    assert err.value.status_code == 422
    assert "Acme" not in str(err.value.detail)
    billing.get_connection.assert_not_called()


class ScopedConn(FakeConn):
    def __init__(self, order_row, store_conn: StoreConn, **kw):
        super().__init__(order_row, **kw)
        self.store = store_conn

    async def fetchrow(self, *args):
        if "SELECT id, rule_version" in args[0]:
            return await self.store.fetchrow(*args)
        return await super().fetchrow(*args)

    async def fetch(self, *args):
        return await self.store.fetch(*args)


@pytest.mark.asyncio
async def test_fulfilment_passes_private_rules_to_generation_and_starts_retention():
    store_conn = StoreConn()
    ref = await store.insert_scope_version(store_conn, ORDER_ID, RULES)
    conn = ScopedConn(_order(bound_scope_ref=ref), store_conn)
    seen = {}

    def generate(order_row):
        seen.update(order_row["scope_rules"])
        return fulfil.GeneratedPack(b"%PDF", "a,b\n", "Southampton", 10, 5)

    deps = _deps(session=_session(metadata={"scope_ref": ref}), generate=generate)
    await fulfil.fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)

    assert seen["excluded_provider_ids"] == ["1-100000001", "1-100000002"]
    assert any("exclusions_purge_after" in c[0] for c in conn.execches)


@pytest.mark.asyncio
async def test_fulfilment_refuses_missing_or_foreign_scope_reference():
    # Order has rules but Stripe metadata does not carry the reference.
    conn = ScopedConn(_order(bound_scope_ref=SCOPE_REF), StoreConn())
    with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="buyer-scope reference"):
        await fulfil.fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=_deps())
    # Metadata carries a reference for an order that has none.
    conn = ScopedConn(_order(), StoreConn())
    deps = _deps(session=_session(metadata={"scope_ref": SCOPE_REF}))
    with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="buyer-scope reference"):
        await fulfil.fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


@pytest.mark.asyncio
async def test_legacy_order_without_rules_is_unchanged():
    conn = FakeConn(_order())
    await fulfil.fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=_deps())
    assert "territory_brief_scope" not in conn.sql_log().replace("territory_brief_scope_versions v", "")


@pytest.mark.asyncio
async def test_purge_dry_run_counts_and_apply_deletes_only_due_rows():
    class PurgeConn:
        def __init__(self):
            self.deletes = []

        async def fetch(self, sql, *args):
            return [{"id": SCOPE_REF}]

        async def execute(self, sql, *args):
            if sql.startswith("DELETE"):
                self.deletes.append(args)
                return "DELETE 3"
            return "UPDATE 1"

        def transaction(self):
            class _Tx:
                async def __aenter__(s):
                    return None

                async def __aexit__(s, *e):
                    return False

            return _Tx()

    conn = PurgeConn()
    dry = await store.purge_expired_exclusions(conn)
    assert dry == {"scope_versions_due": 1, "exclusion_rows_deleted": 0} and conn.deletes == []
    done = await store.purge_expired_exclusions(conn, apply=True)
    assert done == {"scope_versions_due": 1, "exclusion_rows_deleted": 3}


def test_validate_scope_still_accepts_the_checkout_payload_shape():
    scope = validate_scope(
        {"kind": "local_authority", "name": "southampton", "buyer_objective": None,
         "excluded_provider_ids": [], "excluded_location_ids": []},
        CATALOGUE,
    )
    assert not scope.has_buyer_rules
