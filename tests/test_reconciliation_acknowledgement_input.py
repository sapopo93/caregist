"""The acknowledgement input must be reachable, and reachable ONLY manually.

`incremental_update.py` has carried `--acknowledge-unconfirmed-deactivations`
since 3456195, and the finalize refusal names it in its own error text, but the
workflow had no way to pass it — so the documented recovery path was unreachable
from Actions and an operator hitting the refusal had to run the tool by hand.

Exposing it is only safe if a *scheduled* run can never reach it. A scheduled
reconciliation that acknowledged unconfirmed deactivations would record
deactivations the live CQC API never confirmed, which is the one thing the
finalize guard exists to prevent. These tests execute the workflow's real shell
gate rather than substring-matching it, so a future edit that keeps the tokens
but breaks the logic fails here.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(".github/workflows/cqc-reconciliation.yml")


def _workflow() -> dict:
    # BaseLoader keeps `on:` a string rather than YAML 1.1's boolean True.
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _finalize_run_script() -> str:
    """The real `run:` body of the finalize step, straight from the workflow."""
    for job in _workflow()["jobs"].values():
        for step in job.get("steps", []):
            if step.get("name") == "Publish reconciled watermark":
                return step["run"]
    raise AssertionError("finalize step not found")


def _gate(ack: str, event: str, dry_run: str) -> tuple[int, str]:
    """Run the workflow's gate with the given context and report what it did."""
    script = _finalize_run_script()
    # Keep everything up to the python invocation: the gate, not the command.
    gate = script.split("python incremental_update.py")[0]
    gate += 'echo "FLAG=[${ACK_FLAG}]"\n'
    proc = subprocess.run(
        ["bash", "-c", gate],
        env={"PATH": "/usr/bin:/bin", "ACK_INPUT": ack, "EVENT_NAME": event, "DRY_RUN": dry_run},
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def test_the_input_exists_and_defaults_to_false():
    inputs = _workflow()["on"]["workflow_dispatch"]["inputs"]
    ack = inputs["acknowledge_unconfirmed_deactivations"]
    assert ack["type"] == "boolean"
    assert ack["default"] == "false", "must default off; an operator opts in per run"


def test_a_scheduled_run_never_acknowledges():
    """The inputs context is empty on a schedule, so the flag cannot appear."""
    code, out = _gate(ack="", event="schedule", dry_run="")
    assert code == 0
    assert "FLAG=[]" in out


def test_a_scheduled_run_is_refused_even_if_the_input_is_somehow_true():
    """Defence in depth: if a future edit wires an input into the schedule path,
    finalize must fail loudly rather than acknowledge silently."""
    code, out = _gate(ack="true", event="schedule", dry_run="false")
    assert code == 1
    assert "manual-only" in out


def test_a_dry_run_is_refused():
    code, out = _gate(ack="true", event="workflow_dispatch", dry_run="true")
    assert code == 1
    assert "dry run" in out


def test_an_explicit_manual_true_passes_the_flag():
    code, out = _gate(ack="true", event="workflow_dispatch", dry_run="false")
    assert code == 0
    assert "FLAG=[--acknowledge-unconfirmed-deactivations]" in out


@pytest.mark.parametrize("value", ["false", "", "TRUE", "True", "1", "yes", "on"])
def test_anything_other_than_exact_lowercase_true_fails_closed(value):
    code, out = _gate(ack=value, event="workflow_dispatch", dry_run="false")
    assert code == 0
    assert "FLAG=[]" in out, f"{value!r} must not enable acknowledgement"


def test_the_flag_is_spelled_the_way_the_cli_accepts_it():
    cli = Path("incremental_update.py").read_text(encoding="utf-8")
    assert '"--acknowledge-unconfirmed-deactivations"' in cli
    assert "--acknowledge-unconfirmed-deactivations" in _finalize_run_script()


def test_the_flag_is_never_interpolated_directly_into_the_command():
    """The input must be read as data via env, not pasted into the shell line."""
    script = _finalize_run_script()
    command = script.split("python incremental_update.py")[1]
    assert not re.search(r"\$\{\{\s*inputs\.acknowledge", command)
