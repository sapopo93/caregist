from __future__ import annotations

import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone

import pytest

from api.services.customer_package import (
    DOSSIER_FIELDS,
    PackageArtifact,
    PackageBindingError,
    PackageBuildError,
    ProviderSelectionError,
    TERRITORY_TEMPLATE_VERSION,
    WEEKLY_DIGEST_TEMPLATE_VERSION,
    build_package_bytes,
    provider_cohort_from_locations,
    provider_records_from_csv,
    publish_package_atomically,
    verified_snapshot,
)


NOW = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / "fixtures" / "territory_brief"


def brief_snapshot(*, customer: str = "buyer@example.test", cap: int = 50, preview: bool = False):
    return verified_snapshot(
        order_reference="CG-BRIEF-TEST",
        customer_reference=customer,
        product_id="territory-opportunity-brief",
        payment_reference=None if preview else "cs_paid_test",
        template_version=TERRITORY_TEMPLATE_VERSION,
        source_version="CQC-2026-10-29",
        geography="North East",
        service_types=("Homecare Agencies",),
        rating_context_criteria=("historic Requires improvement context",),
        provider_cap=cap,
        buyer_objective="Prioritise responsible outreach research",
        confirmed_at=NOW,
        preview=preview,
    )


def brief_artifacts(count: int = 1) -> dict[str, PackageArtifact]:
    csv_text = "provider_id,location_id,organisation_name\n" + "".join(
        f"P{index:03d},L{index:03d},Provider {index}\n" for index in range(count)
    )
    return {
        "brief.pdf": PackageArtifact("brief.pdf", b"%PDF-1.4 test brief\n%%EOF\n", "application/pdf"),
        "providers.csv": PackageArtifact(
            "providers.csv",
            csv_text.encode(),
            "text/csv; charset=utf-8",
        ),
    }


def providers(count: int) -> list[dict[str, object]]:
    return [
        {
            "provider_id": f"P{index:03d}",
            "provider_name": f"Provider {index}",
            "location_ids": [f"L{index:03d}"],
            "qualification_status": "Qualification incomplete",
        }
        for index in range(count)
    ]


@pytest.mark.parametrize("count", [1, 8, 24, 50])
def test_brief_builds_exact_distinct_provider_cohorts(count: int) -> None:
    built = build_package_bytes(
        brief_snapshot(cap=count),
        brief_artifacts(count),
        provider_records=providers(count),
    )

    assert built.manifest["counts"] == {
        "providers": count,
        "researched_shortlist": 0,
        "qualification_incomplete": count,
    }
    assert len(built.evidence["candidate_register"]) == count
    assert built.evidence["researched_shortlist"] == []


def test_provider_cohort_deduplicates_locations_before_applying_cap() -> None:
    rows = [
        {"provider_id": "P1", "location_id": "L1", "provider_name": "One"},
        {"provider_id": "P1", "location_id": "L2", "provider_name": "One"},
        {"provider_id": "P2", "location_id": "L3", "provider_name": "Two"},
    ]

    cohort = provider_cohort_from_locations(rows, provider_cap=2)

    assert [row["provider_id"] for row in cohort] == ["P1", "P2"]
    assert cohort[0]["location_ids"] == ["L1", "L2"]


def test_provider_cohort_never_truncates_or_pads() -> None:
    rows = [
        {"provider_id": f"P{i}", "location_id": f"L{i}", "provider_name": f"Provider {i}"}
        for i in range(3)
    ]

    with pytest.raises(ProviderSelectionError, match="above the confirmed cap"):
        provider_cohort_from_locations(rows, provider_cap=2)


def test_duplicate_final_provider_is_rejected() -> None:
    duplicate = providers(1) * 2

    with pytest.raises(ProviderSelectionError, match="duplicate provider"):
        build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=duplicate)


def test_researched_dossier_requires_every_acceptance_field() -> None:
    researched = providers(1)[0]
    researched["qualification_status"] = "Researched"
    researched["dossier"] = {field: "evidence" for field in DOSSIER_FIELDS if field != "decision_effect"}

    with pytest.raises(ProviderSelectionError, match="decision_effect"):
        build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=[researched])


def test_complete_researched_dossier_is_separate_from_candidate_register() -> None:
    researched = providers(1)[0]
    researched["qualification_status"] = "Researched"
    researched["dossier"] = {field: f"{field} evidence" for field in DOSSIER_FIELDS}

    built = build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=[researched])

    assert built.manifest["counts"]["researched_shortlist"] == 1
    assert built.evidence["candidate_register"] == []


def test_package_contains_only_confirmed_payloads_and_hashes() -> None:
    built = build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=providers(1))

    with zipfile.ZipFile(io.BytesIO(built.zip_bytes)) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        selection = json.loads(archive.read("selection.json"))
    assert names == set(brief_snapshot().requested_files)
    assert manifest == json.loads(json.dumps(built.manifest))
    assert selection["order_reference"] == "CG-BRIEF-TEST"
    assert selection["customer_reference"] == "buyer@example.test"
    assert selection["payment_reference"] == "cs_paid_test"


def test_missing_requested_core_output_fails_closed() -> None:
    with pytest.raises(PackageBuildError, match="payload mismatch"):
        build_package_bytes(brief_snapshot(), {"brief.pdf": brief_artifacts()["brief.pdf"]})


def test_customer_csv_must_match_validated_provider_roster() -> None:
    mismatched = brief_artifacts()
    mismatched["providers.csv"] = PackageArtifact(
        "providers.csv",
        b"provider_id,location_id,organisation_name\nOTHER,L9,Other Provider\n",
        "text/csv; charset=utf-8",
    )
    with pytest.raises(ProviderSelectionError, match="does not match"):
        build_package_bytes(brief_snapshot(), mismatched, provider_records=providers(1))


def test_malformed_customer_csv_and_pdf_fail_closed() -> None:
    malformed_csv = brief_artifacts()
    malformed_csv["providers.csv"] = PackageArtifact(
        "providers.csv",
        b"provider_id,location_id,organisation_name\nP000,,Provider 0\n",
        "text/csv; charset=utf-8",
    )
    with pytest.raises(ProviderSelectionError, match="missing provider ID"):
        build_package_bytes(brief_snapshot(), malformed_csv, provider_records=providers(1))

    with pytest.raises(PackageBuildError, match="not a complete PDF"):
        PackageArtifact("brief.pdf", b"not a pdf", "application/pdf")


def test_unpaid_build_requires_explicit_preview() -> None:
    with pytest.raises(PackageBuildError, match="payment_reference"):
        verified_snapshot(
            order_reference="CG-1",
            customer_reference="buyer@example.test",
            product_id="weekly-digest",
            payment_reference=None,
            template_version=WEEKLY_DIGEST_TEMPLATE_VERSION,
            source_version="CQC-2026-10-29",
            geography="London",
            confirmed_at=NOW,
        )

    preview = verified_snapshot(
        order_reference="CG-1",
        customer_reference="buyer@example.test",
        product_id="weekly-digest",
        payment_reference=None,
        template_version=WEEKLY_DIGEST_TEMPLATE_VERSION,
        source_version="CQC-2026-10-29",
        geography="London",
        confirmed_at=NOW,
        preview=True,
    )
    assert preview.preview is True
    assert preview.payment_reference is None


def test_atomic_publication_is_retry_safe_and_rejects_wrong_customer(tmp_path) -> None:
    built = build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=providers(1))
    with pytest.raises(PackageBindingError, match="order_reference"):
        publish_package_atomically(
            built,
            root=tmp_path,
            order_reference="WRONG-ORDER",
            customer_reference="buyer@example.test",
        )
    with pytest.raises(PackageBindingError, match="customer_reference"):
        publish_package_atomically(
            built,
            root=tmp_path,
            order_reference="CG-BRIEF-TEST",
            customer_reference="wrong@example.test",
        )
    first = publish_package_atomically(
        built,
        root=tmp_path,
        order_reference="CG-BRIEF-TEST",
        customer_reference="buyer@example.test",
    )
    second = publish_package_atomically(
        built,
        root=tmp_path,
        order_reference="CG-BRIEF-TEST",
        customer_reference="buyer@example.test",
    )
    assert first == second

    with pytest.raises(PackageBindingError, match="customer_reference"):
        publish_package_atomically(
            built,
            root=tmp_path,
            order_reference="CG-BRIEF-TEST",
            customer_reference="wrong@example.test",
        )


def test_interrupted_publication_leaves_no_partial_version(tmp_path) -> None:
    built = build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=providers(1))

    with pytest.raises(PackageBuildError, match="simulated interruption"):
        publish_package_atomically(
            built,
            root=tmp_path,
            order_reference="CG-BRIEF-TEST",
            customer_reference="buyer@example.test",
            fail_before_publish=True,
        )

    order_dir = tmp_path / "CG-BRIEF-TEST"
    assert not (order_dir / built.version).exists()
    assert not list(order_dir.glob(".staging-*"))


def test_concurrent_identical_publications_converge_on_one_package(tmp_path) -> None:
    built = build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=providers(1))

    def publish(_index: int):
        return publish_package_atomically(
            built,
            root=tmp_path,
            order_reference="CG-BRIEF-TEST",
            customer_reference="buyer@example.test",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(publish, range(16)))

    assert len(set(paths)) == 1
    assert paths[0].read_bytes() == built.zip_bytes
    assert not list((tmp_path / "CG-BRIEF-TEST").glob(".staging-*"))


def test_changed_artifact_publishes_a_new_version_without_overwriting(tmp_path) -> None:
    snapshot = brief_snapshot()
    first = build_package_bytes(snapshot, brief_artifacts(), provider_records=providers(1))
    changed_artifacts = brief_artifacts()
    changed_artifacts["brief.pdf"] = PackageArtifact(
        "brief.pdf", b"%PDF-1.4 corrected brief\n%%EOF\n", "application/pdf"
    )
    second = build_package_bytes(snapshot, changed_artifacts, provider_records=providers(1))

    first_path = publish_package_atomically(
        first,
        root=tmp_path,
        order_reference="CG-BRIEF-TEST",
        customer_reference="buyer@example.test",
    )
    second_path = publish_package_atomically(
        second,
        root=tmp_path,
        order_reference="CG-BRIEF-TEST",
        customer_reference="buyer@example.test",
    )

    assert first_path != second_path
    assert first_path.read_bytes() == first.zip_bytes
    assert second_path.read_bytes() == second.zip_bytes


def test_existing_tampered_package_is_not_overwritten(tmp_path) -> None:
    built = build_package_bytes(brief_snapshot(), brief_artifacts(), provider_records=providers(1))
    path = publish_package_atomically(
        built,
        root=tmp_path,
        order_reference="CG-BRIEF-TEST",
        customer_reference="buyer@example.test",
    )
    path.write_bytes(b"tampered")

    with pytest.raises(PackageBindingError, match="conflicts"):
        publish_package_atomically(
            built,
            root=tmp_path,
            order_reference="CG-BRIEF-TEST",
            customer_reference="buyer@example.test",
        )


def test_real_territory_generator_flows_through_shared_builder() -> None:
    from api.services.territory_brief import (
        PurchaseContext,
        brief_to_csv,
        generate_territory_opportunity_brief,
    )
    from api.services.territory_brief_render import render_brief_pdf

    brief = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "Southampton", "window_days": 365, "shortlist_target": 30},
        PurchaseContext(order_reference="CG-BRIEF-TEST", generated_at=NOW, terms_version="test"),
        locations_source=FIXTURE / "locations_detail.jsonl",
        providers_source=FIXTURE / "providers_detail.jsonl",
    )
    csv_text = brief_to_csv(brief)
    provider_records = provider_records_from_csv(csv_text, provider_cap=30)
    built = build_package_bytes(
        brief_snapshot(cap=30),
        {
            "brief.pdf": PackageArtifact("brief.pdf", render_brief_pdf(brief), "application/pdf"),
            "providers.csv": PackageArtifact(
                "providers.csv", csv_text.encode(), "text/csv; charset=utf-8"
            ),
        },
        provider_records=provider_records,
        evidence={"source_provenance": brief.source_provenance},
    )

    assert built.manifest["counts"]["providers"] == len(brief.shortlist) == 30
    assert len({row["provider_id"] for row in built.evidence["candidate_register"]}) == 30


def test_real_digest_renderer_flows_through_shared_builder() -> None:
    from tools.build_weekly_digest_pilot import Window, load_ndjson, render_pdf, select_published_ratings

    window = Window.ending(datetime(2024, 2, 29, tzinfo=timezone.utc).date())
    ratings = select_published_ratings(
        load_ndjson(FIXTURE / "locations_detail.jsonl"), region="South East", window=window
    )
    pdf = render_pdf(
        region="South East",
        window=window,
        issue=1,
        customer="Integration test",
        registrations=[],
        ratings=ratings,
        edition={"source_published_at": "2024-02-29"},
        ratings_source_retrieved_at="2024-03-01T12:00:00+00:00",
    )
    csv_bytes = (
        "section,date,location_id,name,local_authority,detail,cqc_url\n"
        + "".join(
            f"rating_published,{row['published']},{row['location_id']},{row['name']},"
            f"{row['local_authority']},{row['rating']},{row['cqc_url']}\n"
            for row in ratings
        )
    ).encode()
    snapshot = verified_snapshot(
        order_reference="CG-DIGEST-TEST",
        customer_reference="buyer@example.test",
        product_id="weekly-digest",
        payment_reference="cs_paid_digest",
        template_version=WEEKLY_DIGEST_TEMPLATE_VERSION,
        source_version="fixture-2024-02-29",
        geography="South East",
        rating_context_criteria=("issue 1 of 4", "week ending 2024-02-29"),
        confirmed_at=NOW,
    )
    built = build_package_bytes(
        snapshot,
        {
            "digest.pdf": PackageArtifact("digest.pdf", pdf, "application/pdf"),
            "digest.csv": PackageArtifact("digest.csv", csv_bytes, "text/csv; charset=utf-8"),
        },
        evidence={"ratings": ratings},
    )

    assert ratings
    assert built.manifest["product"]["internal_id"] == "weekly_digest_pilot"
    assert set(built.selection["requested_files"]) == set(snapshot.requested_files)
