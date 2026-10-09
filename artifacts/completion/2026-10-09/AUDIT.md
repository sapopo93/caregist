# CareGist completion audit — 9 October 2026

**Verdict: PARTIAL. Engineering corrections are committed on an isolated review branch; this is not commercial acceptance, a merge, or a production release.**

## Current truth

Read-only production probes at 06:08 UTC show frontend and backend serving `59310ecc100119d6d775d70e62db758882bf5b8f`, matching GitHub main after merged PR #82. The primary local branch `audit-fixes-2026-10-06` is its parent `616f9ea`, one merge commit behind. It has no unique commits to merge. Local main is an older reference in another worktree, not the authority for today's production. Latest inspected Production Smoke [37860177962](https://github.com/sapopo93/caregist/actions/runs/37860177962) passed. Evidence: `live-health.json`.

The directory is available, but `/api/v1/health` is degraded and freshness is HTTP 503. The validated source is the September 23 edition, reconciled September 30. The source check reports 213.6 hours since reconciliation against its unchanged 192-hour SLA. This clock differs from the nightly report's 388.9 hours since the source publication date; neither number is a new successful reconciliation. Checkout and delivery remain disabled.

The October 9 saved nightly observation found 126 confirmed identifier defects and two API errors within an incomplete comparison. It used the October 7 directory and classified some records from a cache up to 168 hours old. It is not a fresh live confirmation of every record. Its earlier seven-day window reports 15 completed polls / 28 due fires. The later live probe reports 15 starts / 14 completed, with a poll in progress: different time windows, not contradictory measurements. Configured 28 runs/week × 1,200 locations gives an 11.9-day sweep; measured 15 runs/week gives 22.2 days, both beyond the eight-day promise.

Reconciliation [37595113830](https://github.com/sapopo93/caregist/actions/runs/37595113830) failed on location `1-29608453477` HTTP 404. Current main already contains bounded authoritative-directory 404 retries. The run's single-attempt message must not be represented as proof that today's code lacks retries. Persistent source disagreement is unresolved: no location was skipped, deactivated, backfilled or assigned invented evidence. [CQC's source notice](https://www.cqc.org.uk/about-us/transparency/using-cqc-data) describes publication delays and registration-cancellation lag during its system migration, but does not establish this location's status.

## Fixed on this branch

Six existing PR #83 commits were integrated without replacing main with an old branch. They separate PDF generation and source dates, use public CQC profile links, include CSV licence attribution, disclose shortlist shortages, share the configured price, and gate subscription/application/comparison/export follow-up enqueueing. Paid Brief fulfilment inserts its transactional download email into `pending_emails`; it must not be confused with the separate Radar delivery-outbox path.

A separate Codex technical reviewer reproduced three additional defects. Commit `52b72d1` fixes shortlist/export defects. Its initial global queue guard was rejected by the independent follow-up because paid Brief delivery uses the same queue. Commit `076f100` restores the verified paid-email exception. The next independent recheck found a refund-after-claim race, so the final correction revalidates the order immediately before sending; a real-PostGIS regression confirms the refund defers the email with zero extra sends and no consumed retry:

- The pending email worker refuses marketing claims or sends while outbound is closed. It permits a paid Brief email only when the database confirms a fulfilled order, matching paying address and exact order delivery key; a prefix alone is insufficient. Closing the flag after claim defers unsent rows to pending without consuming retries or moving their due time. Reopening preserves existing delivery/idempotency behavior. An already-issued external request cannot be recalled.
- Shortfall disclosure compares distinct shortlisted providers with the requested target, rather than the internal floor of ten. PDF and CSV carry the same measured quantity and target.
- A zero-provider CSV now contains a header and zero organisation records. The PDF carries the shortage notice; no fake CRM row is generated.

## Claim-to-evidence quality gate

| Promise / intended reader | Observable evidence | Verdict and limit |
|---|---|---|
| Operator can identify current release | Live frontend/backend SHA matches main; PR82 merged | PASS at the saved timestamp |
| Closed outbound stops delayed pending mail | Closed/mid-claim regressions, existing reopening/send tests, and real-SQL paid/marketing/forged/wrong-address/unpaid/refunded/refund-after-claim cases | PASS, mocked Resend; no live send |
| Buyer sees correct dates, source links and licence | Rendered fixture PDF/text and CSV; output regressions | PASS for tested fixtures; not a current customer pack |
| Buyer receives requested shortlist or visible shortage | 8/13/25 and larger distinct-provider cases against requested targets; PDF/CSV assertions | PASS for tested scope quantities; service/buyer fidelity still unaccepted |
| CRM import contains only actual organisations | Zero-shortlist CSV regression | PASS; empty limitation is in accompanying PDF |
| Persistence/download limits are enforced | Real PostGIS integration including 12 download cases and fulfilment/replay | PASS, synthetic Stripe/storage/email |
| Public customer workflows work | 10 synthetic Playwright scenarios against disposable SQL | PASS locally; no real buyer payment/delivery |
| Production data is current and aligned | Live degraded health, failed collector and incomplete nightly comparison | FAIL / PARTIAL; gates remain closed |
| Required independent model acceptance completed | Grok twice broken-pipe; DeepSeek access denied | NOT VERIFIED; no substitution of technical review for named gates |

Final validation of commit `67ee697`: **1,373 backend/PostGIS tests passed, 2 skipped** (standalone TB_PG_URL wrapper and optional transcription mode); **185 frontend tests passed**; **10 synthetic browser journeys passed**; production **Webpack build passed**; Ruff, migration governance, evidence-language guard and diff whitespace checks passed. Normal Turbopack builds hit local loader port-permission errors, including the escalated retry; the alternative build is not a normal Turbopack pass. After the final paid-email correction, **7 targeted tests passed**, including the real-PostGIS mixed-queue and refund-after-claim regression; Ruff passed. The full suite was rerun after that last correction and passed. Imported PR83 previously had green hosted CI, but this combined branch still needs its own hosted CI.

Rendered Southampton fixture: 30 providers, 22-page PDF; Isle of Wight: 8 providers, 10-page PDF. These historical public-source fixtures do not certify the concise buyer promise. The Isle of Wight fixture includes dentists as well as social-care providers: buyer/service-specific qualification remains incomplete. Current commercial promises must be reconciled to a supported, independently reviewed customer scope before sale.

## Uncommitted and unmerged inventory

`PR_INVENTORY.md` lists **33 open PRs**, their divergence and patch equivalence. PR #37 has 12 patch-equivalent commits and is a closure candidate. PR #81 overlaps the existing mandatory real-Postgres Brief journey; it also contains a dependency change that needs separate review. PR #83 is incorporated here but remains open/draft and had no GitHub reviews when inspected. Other old proposals are unreviewed; unmatched patch IDs do not prove a feature is absent. No old PR was blindly merged or closed.

The primary checkout's six modified files and four untracked files were preserved in `/private/tmp/caregist-audit-preservation-20261009`. The four October 8/9 reports, two updated public-source caches and nightly state are also captured under `nightly/` with full hashes in `preserved-nightly.json`. CLI-managed `.projects/state*.json` and generated `frontend/next-env.d.ts` are not product-code fixes and were not swept into a release. The primary dirty files remain unchanged. Three pre-existing stashes remain intact; their contents have not been applied or independently accepted. No worktree or old branch was deleted.

## Required models and remaining work

Hermes CLI invoked Grok 4.6 xhigh, capped at 120 turns, twice; both ended with broken-pipe provider errors. DeepSeek V4 Pro was attempted through the configured gateway and returned HTTP 403 stating this account has no access to the model. No credit purchase or provider configuration change was made. A separate read-only Codex `gpt-6.1-sol` technical reviewer found the three engineering defects and then rejected the initial paid-email regression; it does not fulfil Grok investigation/customer re-test or DeepSeek independent acceptance. Implementation was performed by this Codex session; no claim is made that the historical `gpt-5.6-sol` model ran. Hermes has not completed a model-backed next-step verdict.

Next bounded step: restore the prescribed reviewer access, freeze this branch and evidence, have Grok re-test the changed customer paths, then DeepSeek challenge the packet. Keep the customer/product gates closed. Source-authority resolution and polling-cadence/runtime design need a separate named investigation before collector changes; increasing cadence alone does not prove actual scheduled delivery or historical coverage. Also unresolved: supported service/buyer filter, concise output promise, production generator source adapter, source-effective historical dates, qualification/uncertainty fields, operative terms/consent, financial/provider verification, manual response ownership, paid customer acceptance, and the stale day-7 provider-upgrade CTA whose pricing anchor is absent.

No production deployment, live data/Stripe mutation, customer message, gate opening, PR merge or PR closure occurred. For customer-facing merge/deployment the warroom requires Henry's explicit approval after independent acceptance; this audit does not manufacture that acceptance.
