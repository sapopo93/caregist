from __future__ import annotations

import io
from dataclasses import replace
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone

import pytest

from tests import package_fixtures

from api.services.customer_package import (
    DOSSIER_FIELDS,
    PackageArtifact,
    PackageBindingError,
    PackageBuildError,
    ProviderSelectionError,
    TERRITORY_TEMPLATE_VERSION,
    WEEKLY_DIGEST_TEMPLATE_VERSION,
    build_package_bytes,
    customer_email_reference,
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


def brief_pdf(count: int = 1, *, note: str = "test brief") -> bytes:
    return package_fixtures.brief_pdf("CG-BRIEF-TEST", package_fixtures.roster(count, width=3), note=note, geography="North East")


def brief_artifacts(count: int = 1) -> dict[str, PackageArtifact]:
    csv_text = "provider_id,location_id,organisation_name\n" + "".join(
        f"P{index:03d},L{index:03d},Provider {index}\n" for index in range(count)
    )
    return {
        "brief.pdf": PackageArtifact("brief.pdf", brief_pdf(count), "application/pdf"),
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

    with pytest.raises(PackageBuildError, match="not an openable PDF"):
        PackageArtifact("brief.pdf", b"not a pdf", "application/pdf")


def test_brief_pdf_must_carry_the_validated_roster_hash() -> None:
    artifacts = brief_artifacts()
    artifacts["brief.pdf"] = PackageArtifact("brief.pdf", package_fixtures.plain_pdf("CG-BRIEF-TEST"), "application/pdf")
    with pytest.raises(ProviderSelectionError, match="roster hash"):
        build_package_bytes(brief_snapshot(), artifacts, provider_records=providers(1))

    other_roster = brief_artifacts()
    other_roster["brief.pdf"] = PackageArtifact("brief.pdf", brief_pdf(2), "application/pdf")
    with pytest.raises(ProviderSelectionError, match="roster hash"):
        build_package_bytes(brief_snapshot(), other_roster, provider_records=providers(1))


def test_brief_pdf_must_name_the_selected_order() -> None:
    artifacts = brief_artifacts()
    artifacts["brief.pdf"] = PackageArtifact(
        "brief.pdf",
        package_fixtures.brief_pdf("CG-OTHER-ORDER", package_fixtures.roster(1, width=3)),
        "application/pdf",
    )
    with pytest.raises(PackageBindingError, match="order reference"):
        build_package_bytes(brief_snapshot(), artifacts, provider_records=providers(1))


def test_duplicate_provider_location_row_in_csv_is_rejected() -> None:
    with pytest.raises(ProviderSelectionError, match="duplicate provider/location row"):
        provider_records_from_csv(
            "provider_id,location_id,organisation_name\nP1,L1,One\nP1,L1,One\n", provider_cap=5
        )


def test_customer_email_reference_is_a_normalised_hash() -> None:
    reference = customer_email_reference("  Buyer@Example.TEST ")
    assert reference == customer_email_reference("buyer@example.test")
    assert reference.startswith("email-sha256:") and len(reference) == len("email-sha256:") + 64
    assert "example" not in reference
    with pytest.raises(PackageBindingError):
        customer_email_reference("  ")


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
        "brief.pdf", brief_pdf(note="corrected brief"), "application/pdf"
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
        replace(brief_snapshot(cap=30), geography="Southampton"),
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
    from api.services.customer_package import digest_binding
    from tools.build_weekly_digest_pilot import digest_csv_bytes
    csv_bytes = digest_csv_bytes([], ratings)
    binding = digest_binding(order_reference="CG-DIGEST-TEST", customer_reference="buyer@example.test",
        region="South East", issue=1, week_ending="2024-02-29", csv_bytes=csv_bytes)
    pdf = render_pdf(
        region="South East", window=window, issue=1, customer="Integration test",
        registrations=[], ratings=ratings, edition={"source_published_at": "2024-02-29"},
        ratings_source_retrieved_at="2024-03-01T12:00:00+00:00", binding=binding,
    )
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
        evidence={"generator_manifest": {"binding": binding}, "ratings": ratings},
    )

    assert ratings
    assert built.manifest["product"]["internal_id"] == "weekly_digest_pilot"
    assert set(built.selection["requested_files"]) == set(snapshot.requested_files)


def digest_case(*, csv_bytes=None):
    from api.services.customer_package import digest_binding
    from tools.build_weekly_digest_pilot import digest_csv_bytes
    csv_bytes = csv_bytes if csv_bytes is not None else digest_csv_bytes([], [])
    binding = digest_binding(order_reference="CG-DIGEST-TEST", customer_reference="buyer@example.test",
        region="North West", issue=1, week_ending="2026-10-29", csv_bytes=csv_bytes)
    snapshot = verified_snapshot(order_reference="CG-DIGEST-TEST", customer_reference="buyer@example.test",
        product_id="weekly-digest", payment_reference="cs_paid_digest", template_version=WEEKLY_DIGEST_TEMPLATE_VERSION,
        source_version="fixture", geography="North West", confirmed_at=NOW,
        rating_context_criteria=("issue 1 of 4", "week ending 2026-10-29"))
    artifacts = {"digest.pdf": PackageArtifact("digest.pdf", package_fixtures.digest_pdf(binding, csv_bytes), "application/pdf"),
                 "digest.csv": PackageArtifact("digest.csv", csv_bytes, "text/csv")}
    return snapshot, artifacts, {"generator_manifest": {"binding": binding}}


@pytest.mark.parametrize("field,value", [("order_reference", "OTHER"), ("customer_reference", "OTHER"),
    ("region", "South East"), ("issue", 2), ("window_end", "2026-10-28"), ("csv_sha256", "0" * 64)])
def test_digest_refuses_cross_order_scope_week_and_content(field, value):
    snapshot, artifacts, evidence = digest_case()
    evidence["generator_manifest"]["binding"][field] = value
    with pytest.raises(PackageBindingError):
        build_package_bytes(snapshot, artifacts, evidence=evidence)


def test_digest_refuses_wrong_pdf_and_missing_evidence():
    snapshot, artifacts, evidence = digest_case()
    artifacts["digest.pdf"] = PackageArtifact("digest.pdf", package_fixtures.plain_pdf("Another buyer"), "application/pdf")
    with pytest.raises(PackageBindingError, match="content binding"):
        build_package_bytes(snapshot, artifacts, evidence=evidence)
    with pytest.raises(PackageBindingError, match="missing its canonical"):
        build_package_bytes(snapshot, artifacts)


@pytest.mark.parametrize("bad_date", ["1999-01-01", "2026-10-30", "not-a-date"])
def test_digest_rejects_out_of_window_and_invalid_dates(bad_date):
    csv_bytes = ("section,date,location_id,name,local_authority,detail,cqc_url\n"
        f"new_registration,{bad_date},L1,One,Manchester,Homecare,https://www.cqc.org.uk/location/L1\n").encode()
    snapshot, artifacts, evidence = digest_case(csv_bytes=csv_bytes)
    with pytest.raises(PackageBuildError):
        build_package_bytes(snapshot, artifacts, evidence=evidence)


def test_digest_rejects_duplicate_events():
    row = "new_registration,2026-10-29,L1,One,Manchester,Homecare,https://www.cqc.org.uk/location/L1\n"
    snapshot, artifacts, evidence = digest_case(csv_bytes=(
        "section,date,location_id,name,local_authority,detail,cqc_url\n" + row * 2).encode())
    with pytest.raises(PackageBuildError, match="duplicates an event"):
        build_package_bytes(snapshot, artifacts, evidence=evidence)


def test_bound_buyer_rules_are_immutable_and_visible():
    from dataclasses import replace
    rules = {"buyer_objective": "Assess compliance support", "rule_version": 2,
             "excluded_provider_ids": ["P9"], "excluded_location_ids": []}
    snapshot = replace(brief_snapshot(), buyer_objective=rules["buyer_objective"], scope_rules_json=json.dumps(rules))
    built = build_package_bytes(snapshot, brief_artifacts(), provider_records=providers(1))
    assert json.loads(built.selection["scope_rules_json"]) == rules
    assert built.selection["buyer_objective"] == rules["buyer_objective"]
    assert built.manifest["quality_status"] == "research_incomplete"
    with zipfile.ZipFile(io.BytesIO(built.zip_bytes)) as archive:
        from api.services.customer_package import _pdf_text
        text = _pdf_text(archive.read("selection-confirmation.pdf"), "confirmation.pdf")
    assert "Assess compliance support" in text and "P9" in text
    assert replace(snapshot, scope_rules_json="{}").sha256 != snapshot.sha256


def test_digest_rejects_forged_hash_marker_without_scope_or_event_content():
    snapshot, artifacts, evidence = digest_case()
    binding = evidence["generator_manifest"]["binding"]
    from api.services.pdf_writer import PdfBuilder
    pdf = PdfBuilder(title="Another region and customer")
    pdf.title_block("wrong", [f"Order: {binding['order_reference']}", f"Digest content SHA-256: {binding['sha256']}"])
    artifacts["digest.pdf"] = PackageArtifact("digest.pdf", pdf.build(), "application/pdf")
    with pytest.raises(PackageBindingError, match="geography, issue or observation window"):
        build_package_bytes(snapshot, artifacts, evidence=evidence)


def test_digest_rejects_mismatched_event_details_even_with_expected_marker():
    header = "section,date,location_id,name,local_authority,detail,cqc_url\n"
    good = (header + "new_registration,2026-10-29,L1,Correct,Manchester,Homecare,https://www.cqc.org.uk/location/L1\n").encode()
    snapshot, artifacts, evidence = digest_case(csv_bytes=good)
    binding = evidence["generator_manifest"]["binding"]
    bad = good.replace(b"Correct", b"Wrong customer report")
    artifacts["digest.pdf"] = PackageArtifact("digest.pdf", package_fixtures.digest_pdf(binding, bad), "application/pdf")
    with pytest.raises(PackageBindingError, match="missing or contradicts"):
        build_package_bytes(snapshot, artifacts, evidence=evidence)


def test_preview_watermark_survives_extracting_the_primary_report():
    from api.services.customer_package import _pdf_text
    built = build_package_bytes(brief_snapshot(preview=True), brief_artifacts(), provider_records=providers(1))
    with zipfile.ZipFile(io.BytesIO(built.zip_bytes)) as archive:
        text = _pdf_text(archive.read("brief.pdf"), "brief.pdf")
    assert "PREVIEW - NOT FOR CUSTOMER DELIVERY" in text
