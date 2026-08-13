from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tools.verify_restore_invariants import (
    DUPLICATE_CQC_LOCATION_IDS_QUERY,
    _validate_args,
    verify,
)


def _args(**overrides):
    values = {
        "database_url": "postgresql://example.invalid/db",
        "required_migration": "044_b2b_contract_acceptance.sql",
        "minimum_provider_rows": 50_000,
        "minimum_active_provider_rows": 45_000,
    }
    values.update(overrides)
    return Namespace(**values)


def test_restore_baselines_accept_safe_values():
    _validate_args(_args())


def test_restore_verifier_uses_canonical_cqc_location_identifier():
    assert "SELECT id FROM care_providers" in DUPLICATE_CQC_LOCATION_IDS_QUERY
    assert "SELECT location_id FROM care_providers" not in DUPLICATE_CQC_LOCATION_IDS_QUERY


@pytest.mark.parametrize(
    "overrides",
    [
        {"database_url": None},
        {"required_migration": "../044.sql"},
        {"required_migration": "044.txt"},
        {"minimum_provider_rows": 0},
        {"minimum_active_provider_rows": 50_001},
    ],
)
def test_restore_baselines_reject_unsafe_values(overrides):
    with pytest.raises(ValueError):
        _validate_args(_args(**overrides))


@pytest.mark.asyncio
async def test_restore_verifier_fails_when_source_snapshot_identity_is_missing(monkeypatch):
    conn = AsyncMock()
    transaction = AsyncMock()
    transaction.__aenter__.return_value = None
    transaction.__aexit__.return_value = False
    conn.transaction = MagicMock(return_value=transaction)
    conn.fetchval.side_effect = [True, 60_000, 55_000, 0, "050_source_snapshot_identity.sql"]

    connect = AsyncMock(return_value=conn)
    monkeypatch.setitem(__import__("sys").modules, "asyncpg", SimpleNamespace(connect=connect))
    identity_check = AsyncMock(return_value=False)
    monkeypatch.setattr("api.services.pipeline_health.unique_index_exists", identity_check)

    result = await verify(
        _args(required_migration="050_source_snapshot_identity.sql")
    )

    assert result["checks"]["source_snapshot_identity_present"] is False
    assert result["ok"] is False
    identity_check.assert_awaited_once_with(
        conn,
        "source_snapshots",
        ("source_type", "checksum_sha256"),
    )
    conn.close.assert_awaited_once()
