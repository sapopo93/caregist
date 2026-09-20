# Independent review — report tool at `db513ed` (2026-09-20)

Third review of the nightly-report workstream, second review of this corrective lineage. Reviewer:
`codex exec` with high reasoning effort, model requested `gpt-5.6-sol`, which self-reported as
`gpt-6-astra`; read-only, no production access, worktree left clean. Raw log: `/tmp/review_db513ed.txt`.

## Verdict

```
REVIEWER-VERDICT: FAIL
REVIEWED-SHA: db513ed433c5001bb5e425c75293076c40e2c4b8
REVIEWER-MODEL: gpt-6-astra
FABRICATED-DATA: none found
FINDINGS: 2 high / 3 medium / 1 low
UNVERIFIED: Current production DB/API state was not rerun by instruction. The claimed prior 32/28
classification split is absent from committed parent evidence.
```

## Findings

| Sev | Location | Defect | Required fix |
|---|---|---|---|
| high | `tools/nightly_cqc_db_check.py:1726` | `data_alignment_verdict` treats `summary=None` as zero defects and can return `MATCHED`; sampled or failed input **with** an observed defect returns `MISMATCHED` before incompleteness is considered, instead of `UNVERIFIED` | require a present, full classification summary with no incompleteness before returning either `MATCHED` or `MISMATCHED`; derive completeness inside the verdict path |
| high | `tools/nightly_cqc_db_check.py:1777` | `pipeline_health_verdict` returns `MATCHED` when coverage is absent or `available: false`, if `run_history_status` is `ok` and freshness/sweep pass | require coverage to exist, be available, and contain verified schedule history before any green verdict |
| medium | `tools/nightly_cqc_db_check.py:831` | DB-partial polls remain inside `successful.runs` and `delivered_pct`; reproduced 27 successful / 100% delivered with four partial rows | separate GitHub workflow success from completed polls; compute delivery from completed DB polls |
| medium | `tools/nightly_cqc_db_check.py:3159` | the Markdown report calls coverage `full` and names "live CQC API", omitting that zero records were fetched and all 127 were reused from a 168h cache | render fetched, reused, cache age and TTL beside coverage; describe `full` as population coverage, not a live refresh |
| medium | `tests/test_nightly_cqc_db_check.py:814` | the history regression test uses a different `04:37` window, expects 129 not 127, asserts only loose due/missed bounds, and uses the production cron parser as its own oracle | test the committed `05:11:26Z` window and independently assert 107 + 20 = 127 with exact due and missed counts |
| low | `tools/nightly_cqc_db_check.py:617` | schedule-history epoch compression keeps the **newest** commit of a run of identical cron definitions, so the hourly cron is dated from 3 September when history shows 31 August | build epochs oldest-first, or keep the earliest commit at which each schedule became effective |

## Answer to the question this review was asked to settle

The 32/28 → 20/40 classification shift is **not a laundering of defects**. Independently counted from
the committed raw API fields (`jq`, not the production classifier): 20 Registered dated after
2026-09-16, 40 Registered dated on or before 2026-09-16, 67 Deregistered, zero Registered missing a
date; the second cache holds 57 Registered and 4 Deregistered. Both registration-date classes are
members of `LEGITIMATE_CLASSES`, defect totals are unchanged, and no identifier moved from a defect
class into a benign class. `HEAD~1` reports 60 after / 0 on-or-before, so the 32/28 figure did not come
from the parent commit: the current cache metadata records 40 entries reclassified away from the former
"after" label. The shift is a legitimate consequence of fixing the lexicographic date comparison.

## Independently reproduced by the reviewer

* Schedule history: independent minute-by-minute calculation over 2026-09-13T05:11:26Z → 2026-09-20T05:11:26Z gives old cron 107 fires, new cron 20, due 127; `6bc9880` committed 2026-09-15T10:38:36Z. **The report's own count is right; its named regression test is not.**
* Fail-open verdicts: exercised `build_verdicts` and both verdict functions directly — missing alignment summary → `MATCHED`; absent coverage → `MATCHED`; `available: false` → `MATCHED`; sampled with a defect → `MISMATCHED`; on-disk schedule fallback → `UNVERIFIED`. The on-disk fallback is closed; other missing-evidence paths remain green.
* Dates: **PASS** — the only ordering comparison in the code is between normalised ISO values.
* Committed machine state: **PASS** — no secrets, no personal data, raw snapshot ignored and absent.
* Thresholds: **PASS** — no constant loosened (8d / 16h / 1,200 / 90min / 4h / 250 / 7d).
* Tests: 46 passed, wider suite 966 passed / 34 skipped — **execution PASS, coverage quality PARTIAL**; the new verdict tests call helpers instead of `build_verdicts` with absent summary or coverage, which is why the green paths survive.

## Not established

* The prior 32/28 split is not reproducible from Git — `HEAD~1` carries a 60/0 report and no committed cache.
* The live CQC API fields were not re-fetched; the review establishes consistency with the cache fetched ~35 minutes before the report.
* Production DB state was not checked, by design (the report tool writes artifacts and would dirty the tree).
