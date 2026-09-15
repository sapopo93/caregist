"""Guard the CQC reconciliation schedule against schedule-unsafe inputs.

The workflow is dispatched manually *and* runs on a cron. The `inputs` context is
empty for every event other than `workflow_dispatch`, so an input-derived value
that has no explicit fallback renders empty and crashes the job the cron depends
on: `float(os.environ["SLEEP"])` raises ValueError on "", and `--sleep ""` fails
the shard's `float` argument. A schedule that fails on every tick is worse than
no schedule, so these cases are pinned here.

Two deliberate design choices, because a token-presence check is not a proof:

* The gate conditions are *evaluated* by a small evaluator for the expression
  subset the workflow actually uses, not substring-matched. The evaluator is
  itself anchored to measured GitHub behaviour (below), so a future edit that
  keeps the same tokens but breaks the logic fails here.
* The cadence is *computed* against the published freshness SLA, read from
  `api/services/pipeline_health.py`, rather than asserted in a comment.

Measured anchors — run 34913547890 (workflow `zz-inputs-probe.yml`, a throwaway on
a scratch branch, since removed; a `push` event has the same absent `inputs`
context as a `schedule`):

    inputs.sleep                                      -> ''      (crashes float())
    inputs.sleep || '0.08'                            -> '0.08'  (the fix)
    inputs.dry_run                                    -> ''
    inputs.dry_run == false                           -> true
    github.event_name == 'schedule' || inputs.dry_run == false -> true
    github.event_name != 'schedule' && inputs.dry_run -> falsy

`test_evaluator_matches_measured_runner_behaviour` re-asserts those anchors, so
the model of GitHub's semantics used below cannot silently drift from reality.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(".github/workflows/cqc-reconciliation.yml")
PIPELINE_HEALTH = Path("api/services/pipeline_health.py")

# Jobs that write to production. Each one must run on a schedule, and must say so
# explicitly rather than relying on `inputs.dry_run == false` coercion of an empty
# input.
WRITE_JOBS = {"prepare", "shards", "finalize", "abort-incomplete"}

# The gate, pinned as an exact literal: any behavioural change to the condition
# that decides whether production is written must be a deliberate edit here too.
PINNED_WRITE_GATE = "github.event_name == 'schedule' || inputs.dry_run == false"
PINNED_ABORT_PREFIX = (
    "${{ always() && (github.event_name == 'schedule' || inputs.dry_run == false) && "
)


def _workflow() -> dict:
    # BaseLoader is deliberate and safe: it constructs only strings, never objects
    # (that is what unsafe_load does), and it keeps the `on:` key a string instead
    # of YAML 1.1's boolean True.
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _source() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def render(expr: str, inputs: dict[str, str]) -> str:
    """Render a `${{ inputs.x }}`/`${{ inputs.x || 'literal' }}` interpolation."""
    inner = expr.strip()[3:-2].strip()
    name = inner.split("||")[0].strip().split(".")[-1]
    value = inputs.get(name, "")
    if value:
        return value
    if "||" in inner:
        return inner.split("||", 1)[1].strip().strip("'\"")
    return value


# --------------------------------------------------------------------------- #
# A minimal evaluator for the expression subset this workflow uses.
# --------------------------------------------------------------------------- #

def _tokenize(expr: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch.isspace():
            i += 1
        elif expr.startswith("&&", i) or expr.startswith("||", i) or expr.startswith("==", i) or expr.startswith("!=", i):
            tokens.append(expr[i : i + 2])
            i += 2
        elif ch in "()":
            tokens.append(ch)
            i += 1
        elif ch in "'\"":
            end = expr.index(ch, i + 1)
            tokens.append(expr[i : end + 1])
            i = end + 1
        elif ch.isalpha() or ch == "_":
            j = i
            while j < len(expr) and (expr[j].isalnum() or expr[j] in "_."):
                j += 1
            tokens.append(expr[i:j])
            i = j
        else:
            raise ValueError(f"unsupported character {ch!r} in {expr!r}")
    return tokens


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() != ""


def _coerce(value):
    """GitHub comparison coercion, as measured on run 34913547890."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == "":
        return False
    if text == "true":
        return True
    if text == "false":
        return False
    return value


def evaluate(
    expr: str,
    event_name: str,
    inputs: dict[str, str],
    ref: str = "refs/heads/main",
    needs: dict[str, str] | None = None,
) -> bool:
    """Evaluate an `if:` condition for a given event. Raises on unknown constructs.

    `needs` maps keys like "state_opened" or "prepare.result" to their string
    values, mirroring `needs.<job>.outputs.<name>` and `needs.<job>.result`.
    """
    needs = needs or {}
    inner = expr.strip()
    if inner.startswith("${{") and inner.endswith("}}"):
        inner = inner[3:-2].strip()
    tokens = _tokenize(inner)
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def accept(token: str) -> bool:
        nonlocal pos
        if peek() == token:
            pos += 1
            return True
        return False

    def resolve(token: str):
        if token in ("true", "True"):
            return True
        if token in ("false", "False"):
            return False
        if token == "github.event_name":
            return event_name
        if token == "github.ref":
            return ref
        if token.startswith("inputs."):
            return inputs.get(token.split(".", 1)[1], "")
        if token.startswith("needs."):
            parts = token[len("needs.") :].split(".")
            if "outputs" in parts:
                return needs.get(parts[parts.index("outputs") + 1], "")
            if parts[-1] == "result":
                return needs.get(f"{parts[0]}.result", "")
            return needs.get(token[len("needs.") :], "")
        if token.startswith("'") or token.startswith('"'):
            return token[1:-1]
        raise ValueError(f"unhandled identifier {token!r}")

    def atom():
        nonlocal pos
        token = peek()
        if token == "(":
            pos += 1
            value = or_expr()
            if not accept(")"):
                raise ValueError(f"unbalanced parentheses in {expr!r}")
            return value
        if token == "always":
            pos += 1
            if not (accept("(") and accept(")")):
                raise ValueError(f"expected always() in {expr!r}")
            return True
        if token is None:
            raise ValueError(f"unexpected end of expression {expr!r}")
        pos += 1
        return resolve(token)

    def cmp_expr():
        nonlocal pos
        left = atom()
        token = peek()
        if token in ("==", "!="):
            pos += 1
            right = atom()
            equal = _coerce(left) == _coerce(right)
            return equal if token == "==" else not equal
        return left

    def and_expr():
        value = cmp_expr()
        while accept("&&"):
            right = cmp_expr()
            value = _truthy(value) and _truthy(right)
        return value

    def or_expr():
        value = and_expr()
        while accept("||"):
            right = and_expr()
            value = _truthy(value) or _truthy(right)
        return value

    result = or_expr()
    if pos != len(tokens):
        raise ValueError(f"trailing tokens in {expr!r}")
    return _truthy(result)


# --------------------------------------------------------------------------- #
# Cadence, computed against the SLA the product publishes.
# --------------------------------------------------------------------------- #

def _sla_days() -> int:
    source = PIPELINE_HEALTH.read_text(encoding="utf-8")
    marker = "SOURCE_FRESHNESS_SLA = timedelta("
    assert marker in source, (
        "SOURCE_FRESHNESS_SLA moved; the cadence below is justified by it, so this "
        "test must be updated deliberately rather than skipped"
    )
    body = source.split(marker, 1)[1].split(")", 1)[0]
    days = 0
    for unit, factor in (("weeks", 7), ("days", 1), ("hours", 0), ("seconds", 0)):
        if f"{unit}=" in body:
            value = int(body.split(f"{unit}=", 1)[1].split(",")[0].split(")")[0])
            days += value * factor
    assert days > 0, f"could not read a day-granularity SLA from {body!r}"
    return days


def _cron_days(cron: str) -> set[int]:
    field = cron.split()[4]
    if field == "*":
        return set(range(7))
    days: set[int] = set()
    for part in field.split(","):
        if part.startswith("*/"):
            days |= set(range(0, 7, int(part[2:])))
        elif "-" in part:
            start, end = (int(x) for x in part.split("-"))
            days |= set(range(start, end + 1))
        else:
            days.add(int(part))
    return days


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_evaluator_matches_measured_runner_behaviour():
    """The evaluator above must reproduce what a real runner did (run 34913547890)."""
    assert evaluate("inputs.dry_run == false", "push", {}) is True
    assert evaluate("github.event_name == 'schedule' || inputs.dry_run == false", "push", {}) is True
    assert evaluate("github.event_name != 'schedule' && inputs.dry_run", "push", {}) is False
    assert render(expr="${{ inputs.sleep || '0.08' }}", inputs={}) == "0.08"


def test_schedule_is_declared():
    schedule = _workflow()["on"]["schedule"]
    crons = [entry["cron"].strip() for entry in schedule]

    assert len(crons) >= 2, (
        "the SLA-versus-cadence test below explains why one run a week is not enough; "
        "if this drops to one deliberately, that test must be changed too"
    )
    assert len(set(crons)) == len(crons), "duplicate cron entries"
    for cron in crons:
        assert len(cron.split()) == 5, f"not a 5-field cron expression: {cron!r}"


def test_cadence_absorbs_one_missed_run_within_the_published_sla():
    sla = _sla_days()
    crons = [entry["cron"].strip() for entry in _workflow()["on"]["schedule"]]
    days = sorted({day for cron in crons for day in _cron_days(cron)})
    assert days, f"no day-of-week fields parsed from {crons!r}"

    gaps = [(days[(i + 1) % len(days)] - days[i]) % 7 or 7 for i in range(len(days))]
    if len(days) == 1:
        worst_with_one_missed = gaps[0] * 2
    else:
        worst_with_one_missed = max(gaps[i] + gaps[(i + 1) % len(gaps)] for i in range(len(gaps)))

    assert worst_with_one_missed < sla, (
        f"if one scheduled run is missed or delayed, the source watermark can be "
        f"{worst_with_one_missed} days old against a published {sla}-day SLA, so the "
        f"public page would go stale. Days={days} crons={crons!r}"
    )


def test_write_gates_are_pinned_and_evaluate_true_on_a_schedule():
    jobs = _workflow()["jobs"]

    scheduled = {
        name
        for name, job in jobs.items()
        if "github.event_name == 'schedule'" in (job.get("if") or "")
    }
    assert scheduled == WRITE_JOBS, (
        "every production-writing job must name the schedule event in its `if`, "
        f"so an empty `inputs.dry_run` cannot decide whether it runs; got {scheduled}"
    )

    for name in ("prepare", "shards", "finalize"):
        condition = jobs[name]["if"].strip()
        assert condition == PINNED_WRITE_GATE, f"{name} gate changed: {condition!r}"
        assert evaluate(condition, "schedule", {}) is True, name
        assert evaluate(condition, "workflow_dispatch", {"dry_run": "true"}) is False, name
        assert evaluate(condition, "workflow_dispatch", {"dry_run": "false"}) is True, name

    abort = jobs["abort-incomplete"]["if"].strip()
    assert abort.startswith(PINNED_ABORT_PREFIX), (
        f"the orphaned-batch abort must still run on a schedule and still clean up: {abort!r}"
    )
    assert "state_opened == 'true'" in abort
    assert evaluate(abort, "schedule", {}) is False, (
        "with no batch state opened there is nothing to abort, on any event"
    )
    assert evaluate(
        abort,
        "schedule",
        {},
        needs={"state_opened": "true", "prepare.result": "failure"},
    ) is True, (
        "a scheduled run that opened batch state and then failed must still reach the "
        "abort path; losing this would leave orphaned batches on automatic runs"
    )


def test_dry_run_job_cannot_run_on_a_schedule():
    condition = _workflow()["jobs"]["dry-run"]["if"].strip()
    assert condition == "github.event_name != 'schedule' && inputs.dry_run"
    assert evaluate(condition, "schedule", {}) is False
    assert evaluate(condition, "workflow_dispatch", {"dry_run": "true"}) is True, (
        "manual dry runs must keep working; the change must not disable them"
    )


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
    assert float(render("${{ inputs.sleep || '0.08' }}", {})) == 0.08
    assert float(render("${{ inputs.sleep || '0.08' }}", {"sleep": "0.25"})) == 0.25
    with pytest.raises(ValueError):
        float(render("${{ inputs.sleep }}", {}))


def test_validator_states_the_scheduled_run_contract():
    source = _source()

    assert "a scheduled run takes no resume inputs" in source
    assert "a scheduled run reconciles for real and cannot be a dry run" in source
    assert "production reconciliation writes must run from refs/heads/main" in source
