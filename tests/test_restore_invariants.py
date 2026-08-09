from argparse import Namespace

import pytest

from tools.verify_restore_invariants import DUPLICATE_CQC_LOCATION_IDS_QUERY, _validate_args


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
