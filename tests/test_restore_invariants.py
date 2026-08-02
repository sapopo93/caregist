from argparse import Namespace

import pytest

from tools.verify_restore_invariants import _validate_args


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
