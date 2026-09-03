from pathlib import Path

import yaml


def test_reconciliation_workflow_has_bounded_dynamic_resume_contract():
    workflow = yaml.load(
        Path(".github/workflows/cqc-reconciliation.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert {"resume_batch_id", "resume_run_id"} <= inputs.keys()
    assert workflow["permissions"]["actions"] == "read"
    assert workflow["env"]["SHARD_COUNT"] == "8"
    assert workflow["env"]["ASSUMED_LATENCY_S"] == "1.40"

    strategy = workflow["jobs"]["shards"]["strategy"]
    assert strategy["fail-fast"] == "false"
    assert strategy["max-parallel"] == "4"
    assert "fromJSON" in strategy["matrix"]["shard_index"]
    assert workflow["jobs"]["shards"]["timeout-minutes"] == "330"

    source = Path(".github/workflows/cqc-reconciliation.yml").read_text(encoding="utf-8")
    assert "--phase resume" in source
    assert '--resume-source-run-id "${{ inputs.resume_run_id }}"' in source
    assert "resume_batch_id and resume_run_id must be supplied together" in source
    assert "resume inputs cannot be combined with dry_run=true" in source
    assert "production reconciliation writes must run from refs/heads/main" in source
    assert "needs.prepare.outputs.state_opened == 'true'" in source
    assert "send_monitor_alerts.py" not in source
    assert "--release-sha" in source
    assert "retry" not in strategy
