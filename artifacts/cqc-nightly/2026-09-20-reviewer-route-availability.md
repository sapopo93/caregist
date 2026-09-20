# Independent-reviewer route availability, 2026-09-20

**Purpose:** the audit trail for why the step-2 (ratings, `c192eb6`) and step-3 (report, `72b391c`)
verdicts are outstanding. Step 4 requires reviewer verdicts to be reported; a missing verdict must be
recorded as a route failure, not left silent.

## Route status at 07:47 BST

| Route | Model | State | Evidence |
|---|---|---|---|
| Codex CLI | `gpt-5.6-sol`, effort high | **RATE-LIMITED, re-armed for 08:30 BST** | Both in-flight runs on the report tool died at 07:27 with `exit=1` and "try again at 8:29 AM" after burning 141,514 tokens; the run was cut off mid-answer on the 12-identifier question. A deferred script re-runs both reviews sequentially at the reset (`/tmp/cqc_codex_deferred_reviews.sh`, launched 07:46, verdicts to `/tmp/review_c192eb6_codex2.txt` and `/tmp/review_complete_codex2.txt`). |
| Antigravity `agy` 1.1.27 | `gemini-3.1-pro-high` | **EXHAUSTED, resets in ~168h** | Both replacement reviews died at 07:39-07:40 with `RESOURCE_EXHAUSTED (code 429): Individual quota reached. Please upgrade your subscription to increase your limits. Resets in 167h50m58s.` (`AGY_ERROR`, `exit=3`); outputs are 421 and 423 bytes and contain no verdict. Not a viable substitute for a week. |
| `claude` CLI | — | **DEAD** | "OAuth access token has been revoked". |
| `gemini` CLI | — | **DEAD** | No authentication method configured. |
| Nous gateway (`anthropic/claude-sonnet-5`) | `claude-sonnet-5` | **UNREACHABLE** | "No access token found for Nous Portal login" (exit 1); gateway reported not entitled or unreachable, and `web_search` / `web_extract` were down with it. This is the route the 2026-09-14 routing revision designates for independent review, so the designated route is currently unavailable and the deviation is recorded rather than hidden. |

## Consequence

- The only independent route with capacity inside the next hour is Codex `gpt-5.6-sol` after 08:30.
- The route in use before the 429 (`gemini-3.1-pro-high` via Antigravity) is a different family from the
  DeepSeek builders, so it satisfied the independence requirement while it lasted; it no longer has capacity.
- No verdict has been produced for `c192eb6` (step 2) or for the `72b391c` completion review (step 3).
  Both remain **NOT VERIFIED**; neither is a PASS and neither is a FAIL.
- A reviewer-capacity wall is not evidence about the code. It does not move the merge gate, and it does
  not authorise any automated round to be skipped or self-certified.

## What the Chief of Staff verified independently in the meantime

Because reviewer capacity is the constraint, the independent checks that did not depend on it were run
directly against the frozen revisions and are recorded separately:

- The 12-identifier movement, recomputed and pinned to the `registered_after_snapshot_publication` /
  `registered_on_or_before` boundary (`2026-09-20-twelve-identifier-movement-mapping.md`).
- The finalizer identity guard's concurrency window, reproduced deterministically and observed to commit
  `active_identity_verified: True` with `counts_reconciled: True` while the ACTIVE estate no longer matched
  the manifest (`2026-09-20-finalizer-identity-guard-concurrency-window.md`, reproduction committed
  alongside, `70edcf7`).
- Step-3 question 6: the report-tool suite asserts against the tool's rendered output, its report JSON, its
  cache entries and its audit file, and loads the module for execution via
  `importlib.util.spec_from_file_location`; it does not assert on source text. The ratings-side source-text
  assertions flagged as LOW at `test_migration_governance.py:65` and `test_incremental_update.py:1288` are
  gone at `c192eb6` (0 source-text reads in either file). These are the Chief of Staff's own checks, not
  reviewer verdicts, and are labelled as such.
