"""Guard the authoritative release documents against catalogue-state drift."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
CHECKLIST = (ROOT / "DEPLOYMENT_CHECKLIST.md").read_text(encoding="utf-8")
MASTER_STRATEGY = (ROOT / "docs" / "CAREGIST_MASTER_STRATEGY.md").read_text(encoding="utf-8")
PRICING_ECONOMICS = (ROOT / "pricing_unit_economics.md").read_text(encoding="utf-8")
STRIPE_MANIFEST = (ROOT / "deploy" / "stripe-price-manifest.json").read_text(encoding="utf-8")
STRIPE_ROTATION = (ROOT / "workflows" / "secret-rotation-stripe.md").read_text(encoding="utf-8")
VA_SALES_BRIEF = (ROOT / "docs" / "va-sales-product-spec.md").read_text(encoding="utf-8")
PRICING_SNAPSHOT = (ROOT / "pricing-snapshot.md").read_text(encoding="utf-8")
CLAUDE_GUIDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
LEGACY_AUDIT_PROMPT = (ROOT / "CODEX_AUDIT_PROMPT.md").read_text(encoding="utf-8")
API_SNAPSHOT = (ROOT / "api-landing-snapshot.md").read_text(encoding="utf-8")
SIGNUP_SNAPSHOT = (ROOT / "signup-snapshot.md").read_text(encoding="utf-8")
SWOT = (ROOT / "swot_analysis.md").read_text(encoding="utf-8")
EC2_RUNBOOK = (ROOT / "workflows" / "deploy-ec2.md").read_text(encoding="utf-8")
PRODUCT_SPEC = (ROOT / "product_specification.md").read_text(encoding="utf-8")
BUYER_PERSONAS = (ROOT / "buyer_personas.md").read_text(encoding="utf-8")


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
    assert "Production Neon is on Launch" in MASTER_STRATEGY
    assert "Migration 049 is applied in production" in MASTER_STRATEGY


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


def test_pricing_governance_marks_retired_model_nonoperative_and_checkout_closed() -> None:
    assert "Historical planning model — superseded and non-operative" in PRICING_ECONOMICS
    assert "Radar Regional at £299/month" in PRICING_ECONOMICS
    assert "Radar National at £799/month" in PRICING_ECONOMICS
    assert "Intelligence Feed Pilot from £6,000/year" in PRICING_ECONOMICS
    assert '"checkout_enabled": false' in STRIPE_MANIFEST
    assert "Superseded — historical training material" in VA_SALES_BRIEF
    assert "must not be used with prospects" in VA_SALES_BRIEF
    assert "Superseded historical website snapshot — non-operative" in PRICING_SNAPSHOT


def test_stripe_rotation_runbook_uses_only_current_saleable_prices() -> None:
    assert "Host execution steps are historical" in STRIPE_ROTATION
    for current_name in (
        "STRIPE_PRICE_RADAR_REGIONAL",
        "STRIPE_PRICE_RADAR_NATIONAL",
        "STRIPE_PRICE_INTELLIGENCE_FEED",
    ):
        assert current_name in STRIPE_ROTATION

    for retired_name in (
        "STRIPE_PRICE_ALERTS_PRO",
        "STRIPE_PRICE_STARTER",
        "STRIPE_PRICE_PRO",
        "STRIPE_PRICE_PRO_SEAT",
        "STRIPE_PRICE_BUSINESS",
        "STRIPE_PRICE_PROFILE_ENHANCED",
        "STRIPE_PRICE_PROFILE_SPONSORED",
    ):
        assert retired_name not in STRIPE_ROTATION


def test_active_guidance_and_historical_pricing_artifacts_are_unambiguous() -> None:
    assert "Legacy API tier system (compatibility only)" in CLAUDE_GUIDE
    assert "STRIPE_PRICE_RADAR_REGIONAL" in CLAUDE_GUIDE
    assert "STRIPE_PRICE_RADAR_NATIONAL" in CLAUDE_GUIDE
    assert "STRIPE_PRICE_INTELLIGENCE_FEED" in CLAUDE_GUIDE
    assert "STRIPE_PRICE_ALERTS_PRO" not in CLAUDE_GUIDE
    assert "STRIPE_PRICE_PRO_SEAT" not in CLAUDE_GUIDE
    assert "STRIPE_PRICE_PROFILE_ENHANCED" not in CLAUDE_GUIDE
    assert "Superseded audit prompt" in LEGACY_AUDIT_PROMPT
    assert "Superseded historical website snapshot — non-operative" in API_SNAPSHOT
    assert "Superseded historical website snapshot — non-operative" in SIGNUP_SNAPSHOT
    assert "Historical research only — superseded and non-operative" in SWOT
    assert "Retired production path" in EC2_RUNBOOK
    assert "STRIPE_PRICE_RADAR_REGIONAL" in EC2_RUNBOOK
    assert "STRIPE_PRICE_RADAR_NATIONAL" in EC2_RUNBOOK
    assert "STRIPE_PRICE_INTELLIGENCE_FEED" in EC2_RUNBOOK
    assert "RADAR_CHECKOUT_ENABLED=false" in EC2_RUNBOOK
    assert "RADAR_DELIVERY_ENABLED=false" in EC2_RUNBOOK
    assert "STRIPE_PRICE_ALERTS_PRO" not in EC2_RUNBOOK
    assert "STRIPE_PRICE_PRO_SEAT" not in EC2_RUNBOOK
    assert "Superseded product specification — historical and non-operative" in PRODUCT_SPEC
    assert "Superseded persona research — historical and non-operative" in BUYER_PERSONAS
    assert "is not a canonical deploy path" in STRIPE_ROTATION
