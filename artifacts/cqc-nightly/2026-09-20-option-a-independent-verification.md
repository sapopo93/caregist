# Option A: independent verification of de7ede14 (evidence-completeness gate)

**Date:** 2026-09-20
**Artifact:** `de7ede1445cc9d0a4d7250508cf336de5d719e3a` on `fix/cqc-nightly-report-20260920`
**Parents:** `80724aa` (RLS harness, `tests/integration/conftest.py` only, +84/-6) -> `72b391c` (FAILED review 3)
**Verdict on my own verification: PASS on every check I ran. Independent reviewer verdict: OUTSTANDING.**
This is not the reviewer's verdict. It is the Chief of Staff's own primary evidence, and the reviewer is
required to reproduce or refute every item below.

## What was asked (owner-authorised Option A)

Three rounds each added a guard named after the bad input shown to it. The requirement was therefore
written once, as data: one manifest-driven evidence-completeness gate that every green verdict must pass,
with a property test forbidding a green verdict for any missing, unevaluated, contradictory, unsupported or
unqualified-aggregate element.

## Results, each from a command I ran myself

| Check | Command | Raw result | Exit |
|---|---|---|---|
| Adversarial driver against the real gate (my own, independent of the builder's property test) | `python /tmp/cqc_gate_attack.py` | `ADVERSARIAL RESULT: 22/22 checks passed` | 0 |
| Falsification vs parent | new test file copied into a worktree at `72b391c`, `pytest tests/test_cqc_evidence_completeness.py -q` | `20 failed, 1 passed` | 1 |
| RLS harness at the reviewed SHA | `pytest tests/integration/test_crm_security_invariants.py -q -p no:randomly` | `9 passed in 4.21s` | 0 |
| Full suite at the reviewed SHA, with database | `pytest tests -q -p no:randomly` | `1031 passed, 2 skipped in 39.22s` | 0 |
| Threshold/SLA/cap drift | `git diff 72b391c..de7ede1 -- tools/nightly_cqc_db_check.py` filtered to constant definitions | only the six new `EVIDENCE_*` state strings; no threshold, SLA, grace, cap, sweep or cadence constant added, changed or removed | - |
| Single MATCHED constructor | enumerate every `VERDICT_MATCHED` occurrence in the tool | construction at line 2752 only (`green_verdict`); lines 4216/4218 are comparisons | - |

The two skips are pre-existing environment gates, not the reviewed files:
`test_crm_transcription_local.py` (needs `CAREGIST_RUN_WHISPER_INTEGRATION=1`) and
`test_territory_brief_pg_integration.py` (needs `TB_PG_URL`).

## What the adversarial driver proves

It drives `evidence_completeness_gate` and `green_verdict` directly, with hand-built bundles, for both
domains (`data_alignment`, 14 required elements; `pipeline_health`, 17):

- an empty bundle blocks on every element and yields `UNVERIFIED`, never `MATCHED`;
- each of the five blocking states on a single element blocks and names that element;
- one dropped element out of an otherwise complete bundle blocks and is named;
- an **unlisted** element blocks rather than riding along unexamined;
- a duplicated element name cannot be whitewashed by a later `satisfied` row;
- the negative control (complete bundle) still reaches `MATCHED`.

Honest note: my first run reported 21/22. The single failure was a bug in **my** assertion, not the tool - my
filter excluded the legitimate construction site because the line contains `out: dict`. Corrected and re-run,
the result is 22/22.

## What the falsification proves

The failure mode is behavioural, not a collection error: at `72b391c`, shape A returns
`data_alignment came back MATCHED` with a per-class defect breakdown of 5 against an aggregate of 0, and
shape B returns `pipeline_health came back MATCHED` with 128 attempted runs, 128 due fires, 127 fires with
no matching run and `missed` reading 0. Only `test_17` fails at the parent by `AttributeError`
(`evidence_requirements` did not yet exist); the other 19 fail by observing the fail-open behaviour.

## Design point flagged for the reviewer, not resolved here

Because an unlisted element blocks green, a verdict path that reports an extra diagnostic element would
permanently prevent a legitimate green verdict. The builder's suite passes, which implies the real paths
report exactly the manifest, but the trade-off is a question for the reviewer (prompt item `e`).

## Reproducing

Adversarial driver: `/tmp/cqc_gate_attack.py` (copied to
`artifacts/cqc-nightly/2026-09-20-option-a-gate-attack.py`). Falsification worktree:
`/Users/user/.hermes/worktrees/cqc-falsify-72b391c` (detached at `72b391c`).
