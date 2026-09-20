from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "freshness-watchdog.yml"


def test_freshness_watchdog_installs_the_runtime_import_graph():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "python -m pip install -r requirements-api.txt" in source
    assert "APP_URL: https://caregist.co.uk" in source
    assert "python -m tools.check_new_registration_pipeline" in source


def test_freshness_watchdog_reports_monitor_failure_separately():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "if: always()" in source
    assert "tools/report_watchdog_verdicts.py" in source
