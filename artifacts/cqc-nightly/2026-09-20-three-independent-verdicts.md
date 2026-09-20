# Three independent verdicts, 2026-09-20 (Codex, 08:30 window)

Reviewer: OpenAI Codex, self-reported model `gpt-6-astra`, run via
`codex exec --skip-git-repo-check -c model_reasoning_effort='"high"' -m gpt-5.6-sol`,
read-only, no merge, no deploy, no production run. Different model family from the
DeepSeek builders. All three verdict blocks are verbatim; the evidence sits in
`/tmp/review_c192eb6_codex2.txt` (717,049 bytes), `/tmp/review_complete_codex2.txt`
(882,374 bytes), `/tmp/review_de7ede14_codex.txt` (583,816 bytes).

## 1. Step 2 — ratings corrective at `c192eb6` — FAIL

```
REVIEWER-VERDICT: FAIL
REVIEWED-SHA: c192eb6e46143f0fe0497b1f043ee85d7162ae9e
REVIEWER-MODEL: gpt-6-astra
FABRICATED-DATA: none found
FINDINGS: 2 high / 1 medium / 1 low
PROPERTIES: deregistered-only CONFIRMED | unconfirmed-excluded CONFIRMED | last-published-rating REFUTED
```

- **HIGH** `incremental_update.py:2143` — late count-neutral drift still finalizes
  successfully. This is the concurrency window the Chief of Staff reproduced
  independently; the reviewer reached it separately. Closed by `6ac1888` on
  `fix/cqc-finalizer-guard-20260920` (not in this reviewed SHA).
- **HIGH** `incremental_update.py:1161` — unrecognised current rating text leaves the
  stale current rating persisted: `classify_rating()` maps unfamiliar text to
  `unknown`, but `apply_rating_write_policy()` deliberately leaves `overall_rating`
  unchanged, and public search selects `overall_rating` without consulting
  `rating_state` (`api/queries/providers.py:27`). Consequence: the public search path
  can serve a rating the source no longer publishes. **Open.**
- **MEDIUM** `db/migrations/061_provider_rating_state.sql:30` — rollout is unsafe
  unless ingestion writers are paused: new code selects the new columns
  unconditionally (`incremental_update.py:1216`), so code-before-migration raises
  `UndefinedColumn`, and old ingestion running after 061 can change `overall_rating`
  without updating `rating_state` while the one-time backfill never revisits those
  rows. **Open.**
- **LOW** `incremental_update.py:2459` — CLI help contradicts actual acknowledgement
  behaviour. **Open.**

## 2. Step 3 — report tool completion at `72b391c` — FAIL

```
REVIEWER-VERDICT: FAIL
REVIEWED-SHA: 72b391c7d4b794c20c8dcf397aa81a6e06b5e1da
FABRICATED-DATA: none found
FINDINGS: 4 high / 1 medium / 0 low
```

All six of the operator's questions were answered CONFIRMED, including Q5 (multiple
incomplete-evidence paths still return `MATCHED`; the killed reviewer's eight shapes
remain open) and Q6 (four tests are non-behavioural fixture/prose checks; parent
falsification fails materially rather than vacuously). Also VERIFIED: constants
unchanged, secrets clean, window arithmetic, artifact consistency.

- **HIGH** `:143-149,317-328,1461-1488` — on-or-before registrations absent from the
  snapshot declared legitimate without evidence explaining the absence (40 committed
  rows, including the 12 equality cases).
- **HIGH** `:1918-1969,2128-2171` — alignment trusts aggregate fields without
  validating their per-class breakdown, and treats absent ingestion evidence as
  current. Contradictory or absent aggregates and `ingested=None` each returned
  `DATA ALIGNMENT: MATCHED`.
- **HIGH** `:1585-1685,1689-1721,1930-1969` — cache-only classifications qualify as
  complete evidence: a 188-row full population with `fetched=0`, all rows reused from
  cache, returned `MATCHED`; the committed run used 0/127 live fetches.
- **HIGH** `:863-865,927-965,1972-2125` — pipeline health uses `due minus attempted`
  and ignores fire matching, cancellations, DB failures, DB/GitHub disagreement and
  missing run identities; case B and independent probes for cancelled schedules, DB
  failures and DB disagreement all returned `PIPELINE HEALTH: MATCHED`.
- **MEDIUM** `tests/test_nightly_cqc_db_check.py:358-443,979-1004,1243-1461` — tests
  close specific spellings of missing evidence but do not enforce the invariant.

## 3. Option A — evidence-completeness gate at `de7ede14` — FAIL

```
REVIEWER-VERDICT: FAIL
reviewed-sha: de7ede1445cc9d0a4d7250508cf336de5d719e3a
```

- **HIGH** `:2165` — accepts `classified >= population` and never reconciles
  `classes` with either count. Raw output: `{"blocked_by": [], "case": "OWN1
  classified 68 of population 67; class total 999", "gate_complete": true}`.
- **HIGH** `:3153` and `:3162` — computes the stronger
  `classification_evidence_complete` but passes the weaker `classification_complete`
  into pipeline health, so alignment blocks while health goes green.
- **HIGH** `:1972` and `:2647` — treats caller booleans as an evaluated freshness
  measurement without requiring age or SLA values: `"OWN2 freshness satisfied without
  age_hours or sla_hours"` with `gate_complete: true`.
- **MEDIUM** `:2065` — treats any non-empty checksum value as verified unless an
  optional flag explicitly says false (`"OWN3 arbitrary checksum token with no
  verification flag"`, `gate_complete: true`).
- **LOW** `tests/test_cqc_evidence_completeness.py:689` — registry bookkeeping, not a
  behavioural verdict assertion; replacing `build_verdicts` with a function returning
  garbage still produced `T20_RESULT=PASS_WITH_BUILD_VERDICTS_RETURNING_GARBAGE`.

**What Option A did achieve, confirmed by the reviewer:** one direct `MATCHED`
dictionary at line 2752 and two indirect returns through `green_verdict` (2923, 3114);
calling `green_verdict` without a gate raises
`TypeError: missing 1 required keyword-only argument: 'gate'`; shape A now returns
`UNVERIFIED`. The architecture is right — the remaining defect is that an element can
be marked `satisfied` from a caller boolean rather than a measurement, so the
fail-open moved inside the evaluators.
