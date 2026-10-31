# Two-product builder: engineering and report-quality review, 31 October 2026

## Release boundary

The shared builder was already merged in PR #153 and is served by production SHA
`0653003270175aa24aa6652933c8dfad0a5f07be` (read-only health check on 31 October).
This follow-up is a bounded correctness/preview release, not approval of paid
checkout, automated delivery, researched dossiers, exports or collectors.
Checkout and paid delivery must remain closed; no existing collector, export, claims or outbound configuration is changed. No live customer payment or delivery was exercised.

The full handoff remains **PARTIAL**, not complete: there is no staff website
builder screen, reviewed-dossier ingestion/rendering is not implemented, XLSX is
not a supported requested format, and Weekly Digest sends remain operator-led.
The actual supported product payloads are Brief PDF/CSV and Digest PDF/CSV, plus
selection confirmation, selection/evidence JSON, manifest and a versioned ZIP.
The current customer promise requires source-specific research before a record
can be treated as a completed premium dossier. Passing code tests is not that review.

## Defects reproduced and corrected

- Digest packaging accepted unrelated PDFs/CSV under another order's selection.
  It now checks order/customer/region/week/issue, the canonical CSV hash, dates,
  duplicate events, official source URLs and the PDF's actual labelled event
  register. A PDF carrying the expected hash but no matching scope or event
  contents is refused.
- The payment handler substituted a generic buyer objective. It now carries
  the bound objective/rule version and exclusion counts/hashes. Raw excluded
  IDs remain in the private scope store and its existing purge lifecycle.
- Homecare API names and descriptions did not match the same service filter.
  The generator now uses the shared taxonomy and both source fields.
- A rating-based scope could include other ratings or deregistered locations
  when they had another signal. Provider-group membership is rechecked before
  ranking, and the exact resulting scope is counted.
- The generator/API/database retained a ten-provider requested-cap minimum.
  Migration 074 and request/generator validation permit any cap from 1 to 50.
  Provider deduplication remains before ranking/capping; zero and overflow fail.
- Digest output omitted registration endings. Endings now retain successor,
  dormancy and unresolved context. Absence of a successor is a **closure
  candidate**, never proof that a business closed. Every event has its official
  source in the PDF register and CSV.
- Primary preview PDFs were not watermarked. Every page of every preview PDF,
  including the confirmation, is now stamped as not for customer delivery.
- A small Brief carried territory-wide metadata into dozens of PDF pages.
  The executive table explicitly previews the first eight when necessary;
  Appendix A/CSV retain every selected provider. PDF metadata is scoped to the
  selected locations; full structured coverage remains available separately.
- Delivery wording no longer promises a ready-to-import CRM file. The public
  example now says “up to 50 providers”, with no discarded minimum.

## Claim-to-evidence matrix

| Claim | Evidence / observable result | Verdict |
| --- | --- | --- |
| Both products use the same package boundary | `customer_package.py`, manual adapters, Brief webhook; product integration tests | PASS, engineering scope |
| 1, 8, 24, 50 distinct providers | Generator and real-schema cap tests, duplicate/overflow refusals | PASS |
| Exact order and scope binding | Adversarial wrong-order/week/customer/region/content tests and buyer-rule persistence test | PASS for tested paths |
| Refund/access/replay protection retained | Real-Postgres fulfilment/recovery/download/email-queue tests; Stripe/storage/send are synthetic | PASS for tested paths, not a real merchant receipt |
| Complete premium dossiers | Sample packages contain 0 researched dossiers and 8/50 explicitly incomplete candidates | FAIL for premium acceptance |
| Four-week real Digest operations | Issue-number/retry tests; no four actual inbox/private-file receipts | NOT VERIFIED |
| Current report evidence | Samples use an explicitly historical CQC export retrieved 20 October, newest source date 16 October | NOT current; preview only |
| Complete live Digest | Historical preview does not query the registration ledger and says “not checked” | NOT VERIFIED; not mislabelled as zero registrations |
| PDF layout | Every page rendered; executive/appendix hierarchy and source register inspected; frozen hashes recorded | Bounded visual review, not substantive dossier approval |
| Staff website creation interface | Existing admin handles directory moderation/enquiries, not paid package creation | NOT IMPLEMENTED |

## Verification

- Full Python suite: **1,898 passed, 164 skipped**. Database-dependent skips are
  separately exercised below; remaining skips are not passes.
- Full isolated local PostgreSQL integration suite: **166 passed, 1 skipped**
  (opt-in model-backed local transcription). Creates disposable local databases;
  no production database was used.
- Frontend unit suite: **212 passed**, no failures.
- Ruff, migration governance and diff whitespace checks pass.
- Real public CQC historical inputs produced an 8-provider and a 50-provider
  North West Brief, plus a historical Digest preview. PDF/CSV/manifest counts,
  unique provider IDs, geography/service/rating/registration membership and
  watermark checks are retained in `verification.json` and the local samples.
- The Brief executive section is four pages in both samples. Total report
  lengths are nine and 34 pages, including all candidate/source appendices.
  They remain candidate registers: generic qualification questions do not
  satisfy the frozen template's report-section research standard.

## Release gates and outstanding work

Migration 074 has only been exercised on disposable local PostgreSQL. Its production
application needs the existing recovery/staging and independent-review procedure.
No production change is authorized by this document; Henry's chat instruction
requests release, subject to the project's remaining named gates.

The prescribed Grok retest is not available through this session. The separate
migration 072/073 exception was explicitly bounded to that migration and is not
reused here. An independent approved reviewer must challenge a frozen candidate;
a model usage-limit error is not a completed review. Commercial/report readiness
must not be inferred from a bounded maintenance-release decision.

## Independent challenge and final corrections

Independent GPT-6.1 Terra inspected the frozen implementation, actual PDF previews
and 135 focused checks. It confirmed the Digest/retention/closure corrections and
found no additional blocker for a strictly gated maintenance release, conditional
on all release/migration/Grok gates being separately met. It did not approve full
commercial/report readiness or attest production settings.

Its further report findings were corrected before the final freeze: section 3 now
explicitly distinguishes standing group evidence from recent events, so an older
rating is not represented as a new 90-day event. The executive count label was
shortened to prevent overlap. A new temporal-claim regression and the affected
report suite passed (77 checks). The final preview hashes in `verification.json`
refer to these corrected files. The general premium-dossier limitation remains.

The final wording pass also relabelled the executive totals and sub-area tables
as evidence in scope, not in-window movements, and removed unsupported
onboarding/central-decision assertions. Service-type counts are explicitly
location counts. The final full Python suite passed 1,900 checks (164 skips; before adding the separately executed Digest integration case).

Final source/provenance checks additionally reject raw rating-group membership
when a rating is undated or precedes the current registration. The stale-record
limitation now matches the actual standing-group selection logic. Manual paid
packages bind source-file hashes, refuse changing exports, and Digest database
reads use a repeatable snapshot. A new real-Postgres Digest test exercises ledger
query, region exclusion, renderer, content validation, ZIP publication and wrong-
customer refusal; all three tests in that paired-product integration file pass.
The earlier full integration suite remains 166 passed/one skipped, with this
additional Digest case separately recorded in `digest-postgres-tests.log`.
