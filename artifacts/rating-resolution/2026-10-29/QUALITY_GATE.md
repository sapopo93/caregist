# Producer output-quality gate — local candidate

Verdict: PASS for bounded local acceptance; operating-loop/release verdict PARTIAL pending required reviews. No production or customer delivery claim.

| Promise | Intended reader / truth | Observed output / pass condition | Result |
|---|---|---|---|
| Preserve 20 file-backed values, dates and source | Founder / original ODS hash and frozen audit | All 20 retained; Tillingham qualified unresolved, Chestnuts superseded visibly | PASS |
| Four stale API conflicts show newer evidence | Brief reader / frozen API, file and website | Four chosen values/source/date checked individually; older evidence retained | PASS |
| Two contextual locations remain unresolved | Brief reader / captured provider context | Neither gets current value or numerical/unrated rating-scope membership; candidate values retained | PASS |
| Publication dates and file edition are distinct | Brief reader / file hash, download label, metadata | 2 October download edition; cutoff explicitly unverified | PASS |
| Outputs agree | Brief reader / one resolver | 30 JSON/CSV rows matched; PDF text checked for IDs/dates/values/hashes; visual pages 1, 15, 24, 30 inspected for layout | PASS (representative visual checks) |
| Scope uses the same edition | Enquirer / local real Postgres | Actual TypeScript SQL executed against imported edition and compared to generated rating-group membership; canonical service narrowing exercised | PASS |
| No invented snapshot-change history | Brief reader / API historic sequence only | File-only observation creates no change/published event; no synthetic rating history inserted | PASS |
| Retry/edition integrity | Operator / isolated Postgres | Existing import, immutability, pinned retry and fulfilment checks plus supplemental as-of/future-date regression | PASS |
| Independent operating-loop acceptance | Founder / execution receipts | Grok retest then different-model challenge | PENDING: local queue only |

Receipts: 120 backend tests, 8 isolated local Postgres tests, 9 frontend tests; TypeScript `npx tsc --noEmit` passed. `git diff --check` passed for candidate files. The first Postgres attempt omitted the required URL role and failed fixture setup; rerun with an explicit local role passed. Early implementation failures were fixed before these final receipts.

Limits: no current live website revalidation, national rating audit, production import, hosted frontend/API execution, real paid transaction, delivery, merge or deployment. Visual inspection sampled four PDF pages; full text/content checks cover all 30 fixtures. Synthetic acceptance Brief has artificial scope, provider identities and registration fields as documented in README. No independent model approval is implied.
