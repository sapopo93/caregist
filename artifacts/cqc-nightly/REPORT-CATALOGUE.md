# CQC check — what else it can report

Companion to `tools/nightly_cqc_db_check.py` (job `bc6ed224ad63`, daily 02:00).
Tier 1 ships tonight. Tiers 2–3 are *available*, not promised — each names the
table it would read, so adding one is a small change, not a new project.

## Tier 1 — in the report from tonight

| Report | Source |
|---|---|
| Match verdict: ACTIVE rows vs CQC directory snapshot, with delta | `care_providers`, `pipeline_runs` |
| CQC published a new snapshot (checksum drift) | `source_snapshots.checksum_sha256` |
| Changes by event type in the window | `trusted_event_ledger.event_type` |
| Rating movement direction, and share with no destination rating | `rating_changes`, ledger `new_value` |
| Status transitions with direction (ACTIVE↔INACTIVE) | ledger `old_value`/`new_value` |
| Freshness vs the 192h SLA, watermark age, counts agreement | `trusted_event_ledger.observed_at`, `pipeline_runs` |
| Poll coverage in the last 7 days vs required | `pipeline_runs.run_type='signal_poll'` |
| Run inventory by type/status, failures in window | `pipeline_runs` |
| Data-quality gaps (no rating / region / local authority / geocode) | `care_providers` |
| Refresh churn vs substantive change | `care_providers.updated_at` |

## Tier 2 — computable today, same database

1. **New-registration alerts by territory.** `trusted_event_ledger` already
   carries `new_registration`. Grouped by `care_providers.region` /
   `local_authority` this is a fresh-buyer list each morning — the closest thing
   here to a sales report.
2. **Closure and deregistration watch.** The inverse: ACTIVE→INACTIVE volume by
   territory is the demand signal behind the £495 Market Movement Report.
3. **Ownership and group movement.** `ownership_changed` / `group_movement`
   event types identify consolidation (groups buying independents) — who is
   rolling up a territory.
4. **Rating distribution by region.** `care_providers.overall_rating` ×
   `region` gives a quality heatmap; the same query per territory is a
   ready-made Radar talking point.
5. **Ledger-vs-table drift.** Providers whose ledger events say one thing while
   `care_providers` says another. This is the integrity check that catches a
   half-applied ingest before a client sees it.
6. **Territory coverage gaps.** Where our row count sits well below CQC's for a
   local authority — feeds the territory-intelligence generator directly.
7. **Duplicate detection.** Same normalised name + postcode, distinct IDs.
8. **Contactability gaps.** Rows missing website/phone — these are the
   un-marketed providers, i.e. the warmest cold-start leads.
9. **Rating trend over 12 months.** `rating_changes` history supports
   "improving / deteriorating" per provider and per territory.

## Tier 3 — needs a source we do not hold yet

- **CQC enforcement actions** (requires a CQC enforcement endpoint or published file).
- **Inspection report text** — Docling is already installed for PDF parse; needs the report PDFs.
- **Bed numbers / service-type mix** — the pipeline's field set includes
  `service_types`, `specialisms`, `number_of_beds`, `ownership_type`; confirm
  they are populated before reporting them as fact.

## Not this job's business

Anything client-facing, any outreach, and any write to the database. This job
reads and reports. The reconciliation write path stays with the owner.
