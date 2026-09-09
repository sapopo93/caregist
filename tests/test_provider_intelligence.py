from api.services.provider_intelligence import (
    EvidenceState,
    analyse_provider,
    canonical_url,
    content_sha256,
)


def _provider(**overrides):
    row = {
        "id": "1-10000302982",
        "provider_id": "1-102642938",
        "name": "Henley House",
        "overall_rating": "Good",
        "number_of_beds": "66",
        "website": "https://example.org/home",
        "inspection_report_url": "https://www.cqc.org.uk/location/1-10000302982",
    }
    row.update(overrides)
    return row


def test_missing_public_source_abstains_and_never_publishes():
    result = analyse_provider(_provider(), None, regulator_source_uri="file:///cqc.csv", regulator_source_sha256="a" * 64)
    assert result.identity_state == EvidenceState.VERIFIED
    assert result.proposal_state == EvidenceState.HUMAN_REVIEW
    assert result.publish_allowed is False
    assert "public_source_not_retrieved" in result.review_reasons


def test_rating_and_bed_conflicts_are_explicit():
    result = analyse_provider(
        _provider(),
        {"overall_rating": "Outstanding", "number_of_beds": 70, "website": "https://example.org/home"},
        regulator_source_uri="https://cqc.example/data",
        regulator_source_sha256="b" * 64,
    )
    assert {item.field for item in result.contradictions} == {"overall_rating", "number_of_beds"}
    assert result.proposal_state == EvidenceState.CONFLICTING
    assert result.publish_allowed is False


def test_new_website_is_only_a_review_proposal():
    result = analyse_provider(
        _provider(),
        {"website": "new.example.org/provider"},
        regulator_source_uri="https://cqc.example/data",
        regulator_source_sha256="c" * 64,
    )
    assert result.proposed_updates == {"website": "https://new.example.org/provider"}
    assert "crm_update_requires_human_approval" in result.review_reasons
    assert result.publish_allowed is False


def test_invalid_identity_requires_review():
    result = analyse_provider(_provider(id="unknown"), {}, regulator_source_uri="x", regulator_source_sha256="d" * 64)
    assert result.identity_state == EvidenceState.HUMAN_REVIEW


def test_url_normalisation_rejects_non_http_schemes():
    assert canonical_url("example.org/a//b") == "https://example.org/a/b"
    assert canonical_url("javascript:alert(1)") is None
    assert len(content_sha256("content")) == 64

