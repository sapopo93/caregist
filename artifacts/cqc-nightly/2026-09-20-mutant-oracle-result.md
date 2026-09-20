# Adversarial mutant oracle for the nightly CQC evidence gate — authoring and independent reproduction

**Date:** 2026-09-20 (~09:40 BST) · **Author of the oracle:** independent reviewer route (`codex exec`, model self-reported `gpt-6-astra`, `-c model_reasoning_effort='"high"'`), authored **before** round 5's fix exists, on purpose.
**Subject of measurement:** commit `de7ede1445cc9d0a4d7250508cf336de5d719e3a` (Option A), the reviewed parent — **not** the fix.
**Independent reproduction:** run by the CoS, not self-reported.

## Why this exists

Five review rounds failed in the same shape: each round closed the fail-opens that had been *argued about* and the next reviewer found a shape nobody had named. Prose acceptance criteria let the builder define its own success. This converts that unbounded argument into a bounded, executable, reusable oracle: a fixed set of 36 mutants that either get blocked or do not.

It is deliberately **not** a product test helper and does not live in the product test suite — it is an adversarial instrument held outside the thing it measures.

## The instrument

| | |
|---|---|
| Path | `/Users/user/.hermes/worktrees/cqc-mutants-de7ede14/mutants/evidence_mutant_oracle.py` |
| sha256 | `aa80c97e21f595f4ffc44166866991cfad55817c7db5a58a4218bd5cfce2b74d` |
| Size / lines / mutants | 18,280 bytes · 387 lines · **36 mutants** in 5 families + 1 negative control |
| Invocation | `cd <repo worktree> && PYTHONPATH=. /Users/user/CareGist/.venv/bin/python mutants/evidence_mutant_oracle.py` |
| Import mechanism | `REPO_ROOT = Path(__file__).resolve().parents[1]`, then loads `tools/nightly_cqc_db_check.py` — so **a copy placed in any worktree measures that worktree's code** |
| Exit semantics | **exit 0 only when the negative control reaches `MATCHED` *and* every mutant is blocked.** A non-zero exit is the oracle reporting escapes, **not** an infrastructure failure |
| Negative control | A complete, internally consistent bundle must still reach `MATCHED` — this is what stops "block everything" from scoring as a fix |

**Integrity check:** `git status --porcelain` in the authoring worktree = `?? mutants/` only, `git diff --stat` empty → **the product tool was not modified by the oracle's author.** The measurement is therefore of the parent as reviewed.

## Result at `de7ede14` — independently reproduced

Command run by the CoS, output `/tmp/oracle_rerun.txt` (3,551 bytes):

```
CONTROL STATUS=MATCHED alignment=MATCHED pipeline=MATCHED
...
SUMMARY mutants=36 blocked=13 escaped=23 negative_control=MATCHED
exit=1
```

**36 mutants · 13 blocked · 23 escaped · control MATCHED.** Identical to the author's report — the self-report is confirmed, not trusted.

| Family | Blocked | Escaped |
|---|---|---|
| `boolean-as-measurement` (M01–M06) | **6** | **0** |
| `count-total-inconsistency` (M07–M12, M29–M34, M35) | 6 | **7** — M07, M08, M09, M10, M11, M12, M35 |
| `freshness-without-measurement` (M13–M18) | 0 | **6** — M13–M18 |
| `unverified-checksum` (M19–M22) | 0 | **4** — M19–M22 |
| `provenance-layer` (M23–M28, M31, M36) | 2 | **6** — M23–M28 |
| `known-shape` (M29–M36) | 6 | 1 — M35 |

### The 23 escaping mutants (the acceptance case list)

- **Count/total inconsistency:** `classified_68_of_population_67` · `legitimate_class_aggregate_is_999_for_a_population_of_10` · `aggregate_class_totals_sum_to_9_while_classified_is_10` · `per-class_classes_sum_to_11_while_population_is_10` · `zero_population_with_one_classified_identifier` · `snapshot_population_99_but_diff_accounts_for_100` · `DB_and_GitHub_run_records_disagree_without_a_failed_DB_status`
- **Freshness without measurement:** `signal_has_no_age_hours` · `signal_has_no_sla_hours` · `signal_says_evaluated_but_comparison_is_unstated` · `source_has_no_age_hours` · `source_has_no_sla_hours` · `source_says_evaluated_but_comparison_is_unstated`
- **Unverified checksum:** `valid-looking_token_with_verification_outcome_absent` · `…_None` · `…_empty` · `non-empty_token_marked_unverified_as_text`
- **Provenance layer:** `entity_count_is_a_fabricated_constant` · `classification_measurement_predates_its_attributed_snapshot` · `classification_value_copied_from_a_different_element` · `signal_age_attributed_to_workflow_YAML,_which_has_no_observation_timestamp` · `completed-poll_value_copied_from_expected_fires` · `snapshot_checksum_attributed_to_a_source_incapable_of_producing_file_bytes`

## Interpretation

1. **Option A's success is real but narrow.** It closed the entire `boolean-as-measurement` family — 6 of 6 blocked — and 6 of the 8 known shapes. That is a verified partial result, the first non-zero movement in five rounds.
2. **The fail-open is not one hole, it is four families.** 23 escapes: count reconciliation, freshness measurement, checksum verification, and provenance.
3. **The pre-registered prediction was correct.** Round 5's stop rule (`73b2841`), written before this result existed, predicted that a surviving failure would live in the **provenance layer** — a well-formed measurement never derived from the data it claims. Six escapes sit exactly there, including a fabricated constant and a checksum attributed to a source incapable of producing file bytes.
4. **The regress now has a terminator.** "Escaped = 0 on this frozen 36-mutant set with the control still MATCHED" is a bounded, falsifiable, re-runnable criterion. It is now the acceptance instrument for round 5: `sa-0-bce56c4e` has been steered with the full escaping list, the exact command, and the immutable-oracle constraint (no editing, deleting, weakening or special-casing the oracle, or the mutants).

## Limits — what this does NOT establish

- Mutants are **constructed evidence bundles**, not a live nightly run against production caches. The standing caveat is unchanged.
- It bounds **these 36 shapes**, not all shapes. A 37th family could still exist; escaped=0 is necessary, not sufficient.
- It measures the **verdict layer only** (the gate and its evaluators), not ingestion, reconciliation or any production path.
- A green oracle run at a fix SHA is a **precondition for review**, never a substitute for it, and never a release verdict.
