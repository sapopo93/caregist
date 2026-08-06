from __future__ import annotations

from api.service_taxonomy import canonical_service_rows, resolve_service_filter, taxonomy


def test_taxonomy_covers_all_observed_cqc_service_labels():
    aliases = [alias for entry in taxonomy() for alias in entry["aliases"]]

    assert len(aliases) == 57
    assert len({alias.casefold() for alias in aliases}) == 57


def test_canonical_and_legacy_filters_resolve_to_same_exact_aliases():
    canonical = resolve_service_filter("home-care")
    legacy = resolve_service_filter("Homecare Agencies")

    assert canonical == legacy
    assert canonical == ("domiciliary care service", "homecare agencies")


def test_raw_counts_are_aggregated_under_stable_canonical_slug():
    rows = canonical_service_rows(
        [
            {"service_type": "Homecare Agencies", "provider_count": 100},
            {"service_type": "Domiciliary care service", "provider_count": 5},
        ]
    )

    home_care = next(row for row in rows if row["service_type"] == "home-care")
    assert home_care["service_name"] == "Home Care"
    assert home_care["provider_count"] == 105
