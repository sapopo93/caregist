# The finalizer's identity guard is defeated by a concurrent substitution

**Date:** 2026-09-20
**Reviewed artifact:** `c192eb6` (`fix/cqc-ratings-schema-20260920`), guard at `incremental_update.py:2154-2157`, commit at `:2284`
**Status:** REPRODUCED DEFECT (primary evidence, independently executed). Not a review verdict.
**Reproduction:** `2026-09-20-finalizer-guard-race-repro.py` (scratch module, run in a throwaway worktree at `c192eb6`; no product file changed)

## The claim under test

Henry's step-1 requirement for the finalizer guard reads, verbatim:

> compare the exact ACTIVE ID SET against the expected ID set after all writes, **under locking or
> transaction isolation that prevents concurrent identity substitution**, and record and reject missing
> and extra IDs separately

`c192eb6` satisfies three of the four clauses. It compares the exact id set (not the count its
predecessor compared), it records missing and extra ids separately, and it names both in the refusal.
It does **not** satisfy the isolation clause: the comparison is a read taken inside a READ COMMITTED
transaction, with no lock and no predicate protection.

## The window

```
:2154  SELECT id::text FROM care_providers WHERE UPPER(status) = 'ACTIVE'   <- the verification read
:2158  missing_active_ids / extra_active_ids computed; refusal if any        <- the decision
:2226  UPDATE reconciliation_batches SET status = 'completed', ...           <- the attestation
:2265  json.dumps({"fullCoverage": True, ...})
:2284  conn.commit()                                                         <- the durability point
```

A substitution committed by any other transaction **after `:2154` and before `:2284`** is invisible to
the guard, is preserved by its commit, and is certified by the `active_identity_verified: True` row it
writes. The precedent for this being reachable in production is the production wiring itself: the CQC
directory poll and this finalizer both write `care_providers.status`, which is why the guard exists.

## How it was pinned deterministically

The success path makes exactly one `json.dumps` call between the read and the commit (`:2265`, inside the
`UPDATE pipeline_runs` arguments; the other `fullCoverage` occurrences are SQL text at `:1731`, `:2383`,
`:2437`). The reproduction wraps that call and releases it only after the substitution has been
committed from a second connection. Nothing in the product code is modified, and the ordering is
guaranteed rather than raced:

```
guard read  <  substitution commit  <  finalizer commit
```

## Observed result

Substitution: manifest member `1-10007` set `INACTIVE`, unexplained location `1-97001` inserted `ACTIVE`.
Count-neutral by construction: 100 manifest locations, one leaves, one joins.

| Read back from the same database after the finalize committed | Value |
|---|---|
| finalize return code | `0` |
| `reconciliation_batches.status` | `completed` |
| `pipeline_runs.status` / `counts_reconciled` | `completed` / `True` |
| `deactivation_confirmation.active_identity_verified` | `True` |
| `deactivation_confirmation.missing_active_ids` | `[]` |
| `deactivation_confirmation.extra_active_ids` | `[]` |
| `expected_active_ids_count` / `active_after_ids_count` | `100` / `100` |
| true `ACTIVE` estate: `1-10007` still ACTIVE / `1-97001` ACTIVE | `False` / `True` |

The batch attests, in its own committed row, to an identity set that the estate does not have. This is
the same defect class as a green verdict issued without complete evidence: the finalizer's `MATCHED`
equivalent is reachable without the evidence it claims to have checked.

## Scope and severity, stated precisely

- **Not** a data-corruption defect. The estate drift is exactly what was committed; nothing is invented.
- It is a **false-assurance defect**. `active_identity_verified: True` plus `counts_reconciled: True`
  can be committed while the ACTIVE set disagrees with the manifest by two identities.
- It requires a concurrent writer inside a sub-millisecond window, but not a rare one: polling
  ingestion writes `care_providers.status` on its own schedule, independent of the reconciliation run.
- The guard remains a strict improvement over its predecessor, which compared only the total ACTIVE
  count and would have missed this drift *even without concurrency*. The sequential case is genuinely
  closed and is proven by the reviewed test suite.
- The builder disclosed this window in its handover. This reproduction confirms the disclosure is
  accurate and supplies the missing falsification control.

## Why the first attempt proved nothing

An earlier attempt pinned the finalizer with `SELECT ... FOR UPDATE` on its `reconciliation_batches`
row. The finalizer completed without an observed wait, so the attempt established no interleaving and
was discarded rather than reported as evidence. The pin was replaced with the deterministic hook above.
No conclusion is drawn from the discarded attempt.

## Required corrective (bounded)

Close the window, or record the drift it permits, without weakening any existing refusal:

1. Predicate protection on the verification read (SERIALIZABLE or an equivalent that aborts the commit
   rather than certifying a stale set); or
2. a cooperative lock taken by every writer of `care_providers.status` (poller and finalizer); or
3. post-commit re-verification in a fresh transaction that marks the batch failed, naming the drift,
   instead of leaving it certified.

The corrective must reproduce this module's interleaving as a permanent regression test that fails
against `c192eb6` and passes after the change, and must not loosen the existing refusal paths.
