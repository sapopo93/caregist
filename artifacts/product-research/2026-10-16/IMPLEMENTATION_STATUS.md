# Implementation status against the five stages (16 Oct 2026)

Basis: the revised position paper and the evolution plan as pasted into the project thread (the two files themselves are on the founder's Mac and were not readable from this cloud container), the repo at `main` 2332889, `.warroom/` records, and GitHub Actions logs read via the GitHub connector. Environment limits: no route to cqc.org.uk, the CQC API or api.caregist.co.uk (egress proxy refuses them), no production `DATABASE_URL`, no Stripe or mailbox access. `asyncpg` would not build, so the full suite was not run locally; CI runs it.

| Stage | Verdict | Evidence / location | Blocker |
|---|---|---|---|
| 1. Verify and repair collection | PARTIAL | PR #90: report-index health classification (`tools/poll_cqc_signals.py`), 9 tests, CI green on first commit. Run history: `artifacts/collection-evidence/2026-10-16/report-index-history.md` (7 of 623 runs; 6 zero, 1 with 3). | Cannot see what CQC returns to the poller, check robots/permission, test API suitability, measure per-route latency or reconcile matched populations without CQC and production access. A WebFetch of the CQC search URL was refused as robots-disallowed. |
| 2. Backfill dry run | NOT RUN | `tools/backfill_rating_change_dates.py` reviewed: dates only differing published grades on the latest row with a matching current rating and an eligible CQC date; never invents dates. | Needs production read access (`DATABASE_URL`). Not run, so no eligible/skipped counts exist. |
| 3. Buyer-specific Brief | PARTIAL: generator, PDF and CSV only | `api/services/territory_brief.py`, `territory_brief_render.py`: optional objective, identifier-only provider/location exclusions, rule version; exclusions applied before ranking, never listed; PDF and CSV carry objective and version; legacy scopes unchanged (stable JSON shape, no new CSV columns). `tests/test_territory_brief_buyer_rules.py` (8 test functions). | Enquiry, coverage, order table, Stripe metadata and frontend are not changed (see below). |
| 4. Complete sample Brief | NOT DONE | Synthetic render only: `/mnt/project-files/reviews/demo-synthetic-brief/` (labelled synthetic). Inspected: rule lines render, excluded provider absent from PDF and CSV. | Needs production source data, a named buyer scope and a fair free-CQC comparison. No customer validation exists or is claimed. |
| 5. Delivery and economics | NOT DONE | None. | Authorised test journey (Stripe test payment, generation, independent check, private download, receipt, failure recovery) needs payment/inbox/staff access and an open gate. |

## Remaining Stage 3 plumbing (proposed, not built, needs approval: migration and checkout path)

1. Migration `066`: nullable `buyer_objective`, `excluded_provider_ids`, `excluded_location_ids` and `rule_version` on the order (or a `territory_brief_scope_versions` table keyed by order). Existing rows stay NULL.
2. Stripe metadata is immutable and size-limited: carry only `scope_rule_hash`, compare it at fulfilment as the existing scope fields are, and read the full rules from the order row. Do not put the exclusion list in metadata.
3. Enquiry and `TerritoryScopePicker` fields for objective and exclusions; coverage check run against the same rules; amendments become a new `rule_version`.
4. Confidentiality: restricted access to exclusion lists, a retention/deletion period set by the founder, and tests that one order's list never reaches another's output.

## Gates reported blocked, not substituted

- The prescribed reviewers (Grok, Codex, DeepSeek) are not available in this session. No independent review has been done on any item here.
- The `output-quality-gate` skill is not in this session's skill list, so it was not applied.

## Owner decisions still needed

F1 first buyer segment; F2 the sample buyer and a production-data run; approval to run the backfill dry run against production read-only; approval of the Stage 3 migration and Stripe-metadata approach; the exclusion-list retention period; terms copy (fix list S9); who ran or cancelled the 14 Oct reconciliation.
