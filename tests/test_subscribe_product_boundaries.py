"""Keep free-subscription emails aligned with the two-offer catalogue."""

from pathlib import Path


SOURCE = Path(__file__).parents[1] / "api" / "routers" / "subscribe.py"


def test_free_search_drip_does_not_promote_stopped_alert_products():
    source = SOURCE.read_text(encoding="utf-8")
    assert "Upgrade for instant alerts" not in source
    assert "Set up monitoring alerts" not in source


def test_free_search_drip_describes_weekly_pilot_without_subscription_claim():
    source = SOURCE.read_text(encoding="utf-8")
    assert "one-off four-week pilot" in source
    assert "observation-dated" in source
    assert "You'll receive weekly CQC rating changes" not in source
