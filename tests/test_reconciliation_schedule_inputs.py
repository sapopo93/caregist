"""Guard the CQC reconciliation schedule against schedule-unsafe inputs.

The workflow is dispatched manually *and* runs on a cron. The `inputs` context is
empty for every event other than `workflow_dispatch`, so an input-derived value
that has no explicit fallback renders empty and crashes the job the cron depends
on: `float(os.environ["SLEEP"])` raises ValueError on "", and `--sleep ""` fails
the shard's `float` argument. A schedule that fails on every tick is worse than
no schedule, so these cases are pinned here.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(".github/workflows/cqc-reconciliation.yml")

# Jobs that write to production. Each one must run on a schedule, and must say so
# explicitly rather than relying on `inputs.dry_run == false` coercion of an empty
# input.
WRITE_JOBS = {"prepare", "shards", "finalize", "abort-incomplete"}


def _workflow() -> dict:
    # BaseLoader is deliberate and safe: it constructs only strings, never objects
    # (that is what unsafe_load does), and it keeps the `on:` key a string instead
    # of YAML 1.1's boolean True.
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _source() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def render(expr: str, inputs: dict[str, str]) -> str:
    """Render a `${{ inputs.x }}`/`${{ inputs.x || 'literal' }}` expression.

    Mirrors GitHub's semantics that matter here: an unset input is the empty
    string, and `||` falls through to the literal when the left side is empty.
    """
    inner = expr.strip()[3:-2].strip()
    name = inner.split("||")[0].strip().split(".")[-1]
    value = inputs.get(name, "")
    if value:
        return value
    if "||" in inner:
        return inner.split("||", 1)[1].strip().strip("'\"")
    return value


def test_schedule_is_declared_and_backs_the_freshness_sla():
    workflow = _workflow()
    schedule = workflow["on"]["schedule"]
    crons = [entry["cron"] for entry in schedule]

    assert len(crons) >= 2, (
        "a single weekly run leaves one day of margin against the 8-day "
        "SOURCE_FRESHNESS_SLA, so one missed run publishes stale data"
    )
    assert len(set(crons)) == len(crons), "duplicate cron entries"
    for cron in crons:
        assert len(cron.split()) == 5, f"not a 5-field cron expression: {cron!r}"


def test_every_write_job_runs_on_a_schedule_explicitly():
    workflow = _workflow()
    jobs = workflow["jobs"]

    scheduled = {
        name
        for name, job in jobs.items()
        if "github.event_name == 'schedule'" in (job.get("if") or "")
    }
    assert scheduled == WRITE_JOBS, (
        "every production-writing job must name the schedule event in its `if`, "
        f"so an empty `inputs.dry_run` cannot decide whether it runs; got {scheduled}"
    )

    for name in WRITE_JOBS:
        condition = jobs[name]["if"]
        assert "inputs.dry_run == false" in condition, name
        assert "github.event_name == 'schedule'" in condition, name


def test_dry_run_job_cannot_run_on_a_schedule():
    condition = _workflow()["jobs"]["dry-run"]["if"]
    assert "github.event_name != 'schedule'" in condition


def test_sleep_is_never_rendered_bare():
    source = _source()

    assert "${{ inputs.sleep }}" not in source, (
        "a bare `inputs.sleep` renders empty on a schedule and crashes the "
        "projection step and the shard CLI"
    )
    assert source.count("${{ inputs.sleep || '0.08' }}") == 2, (
        "expected the explicit sleep fallback on both the projection env and the shard CLI"
    )


def test_sleep_fallback_matches_the_input_default():
    inputs = _workflow()["on"]["workflow_dispatch"]["inputs"]
    default = inputs["sleep"]["default"]
    source = _source()

    fallback = source.split("${{ inputs.sleep || '", 1)[1].split("'", 1)[0]
    assert fallback == default, (
        f"schedule fallback {fallback!r} must match the dispatch default {default!r}, "
        "or a scheduled run and a manual run would poll CQC at different rates"
    )


def test_sleep_renders_as_a_float_for_a_schedule_and_for_a_dispatch():
    # A schedule supplies no inputs at all.
    assert float(render("${{ inputs.sleep || '0.08' }}", {})) == 0.08

    # The fallback must not override an explicit dispatch value.
    assert float(render("${{ inputs.sleep || '0.08' }}", {"sleep": "0.25"})) == 0.25

    # The counterexample this fallback exists for: the bare form cannot be parsed.
    with pytest.raises(ValueError):
        float(render("${{ inputs.sleep }}", {}))


def test_validator_states_the_scheduled_run_contract():
    source = _source()

    assert "a scheduled run takes no resume inputs" in source
    assert "a scheduled run reconciles for real and cannot be a dry run" in source
    assert "production reconciliation writes must run from refs/heads/main" in source
