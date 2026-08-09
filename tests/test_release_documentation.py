"""Guard the authoritative release documents against catalogue-state drift."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
CHECKLIST = (ROOT / "DEPLOYMENT_CHECKLIST.md").read_text(encoding="utf-8")
MASTER_STRATEGY = (ROOT / "docs" / "CAREGIST_MASTER_STRATEGY.md").read_text(encoding="utf-8")


def test_authoritative_documents_do_not_claim_paid_release_is_green() -> None:
    combined = "\n".join((README, CHECKLIST, MASTER_STRATEGY))

    assert "Production release is GO" not in combined
    assert "Production is **GO**" not in combined
    assert "Database on paid Launch plan" not in combined
    assert "Neon Postgres runs on the Launch plan" not in combined
    assert "corrected website is not deployed" not in combined
    assert "live pricing page remains legacy" not in combined

    assert "paid Radar release is not yet approved" in README
    assert "paid Radar release is **NO-GO**" in CHECKLIST
    assert "Production Neon is on Free" in MASTER_STRATEGY


def test_operational_checklist_uses_only_the_final_saleable_price_names() -> None:
    for current_name in (
        "stripe_price_radar_regional",
        "stripe_price_radar_national",
        "stripe_price_intelligence_feed",
    ):
        assert current_name in CHECKLIST

    for retired_name in (
        "stripe_price_alerts_pro",
        "stripe_price_starter",
        "stripe_price_pro_seat",
        "stripe_price_business",
        "stripe_price_profile_enhanced",
        "stripe_price_profile_premium",
        "stripe_price_profile_sponsored",
    ):
        assert retired_name not in CHECKLIST
