# Territory Brief verdict check — 1 October 2026

**Verdict: keep the product candidate; do not sell the current recent-rating-change edition or describe fulfilment as automated.** The production database is available and the overall source-health check is fresh, but the paid generator still depends on raw NDJSON, the rating ledger cannot measure source-effective recency, and the promised organisation count and Excel output need correction. A registration-focused brief has measurable supply in broader scopes. That is evidence for further qualification, not proof of paying demand, renewal or release acceptance.

This is read-only producer research. No production data, product code, commercial flag, gate, payment, deployment or outbound delivery was changed. The first three queries below are the user's supplied SQL. SQL and raw outputs are saved in `territory-verdict-query-results.json`; transaction read-only was `on`. Initial queries were observed at 2026-10-01T16:26:27Z; supplemental queries were collected afterwards on the same date, not as one atomic snapshot.

## Requested query results

```sql
SELECT min(effective_date), max(effective_date), count(*)
FROM trusted_event_ledger WHERE event_type = 'rating_changed';
```

| min | max | count |
|---|---|---:|
| NULL | NULL | 34,332 |

```sql
SELECT count(*) AS events, count(DISTINCT t.provider_id) AS orgs
FROM trusted_event_ledger t
JOIN care_providers cp ON cp.id = t.location_id
WHERE t.event_type = 'rating_changed'
  AND t.effective_date >= current_date - 90
  AND cp.region = 'London'
  AND cp.service_types ILIKE ANY (ARRAY['%domiciliary%', '%homecare%']);
```

| events | orgs |
|---:|---:|
| 0 | 0 |

**Interpretation:** all 34,332 `rating_changed` rows have NULL `effective_date` and NULL `effective_at`. SQL's date predicate excludes them. The zero therefore means the ledger cannot answer this recency question; it does not establish that no CQC rating changed. Widening to national geography produces the same zero because it does not repair the missing dates.

Observed timestamps span 10 August to 20 September 2026. Observation is ingestion time, not rating publication time. Across the entire ledger there is only one candidate pair whose old and new text both match recognised grades (Good → Inadequate), still without an effective date. It is not an independently verified transition. The initial product research's 30-day window contained no such pairs. Do not substitute `observed_at` for publication dates or market initial/bootstrap records as recent downgrades.

```sql
SELECT left(last_inspection_date::text, 4) AS yr, count(*)
FROM care_providers
WHERE region = 'London' AND overall_rating ILIKE 'requires improvement'
GROUP BY 1 ORDER BY 1;
```

| yr | count |
|---|---:|
| 2017 | 1 |
| 2019 | 5 |
| 2020 | 5 |
| 2021 | 34 |
| 2022 | 95 |
| 2023 | 101 |
| NULL | 33 |
| **Total** | **274** |

This SQL covers all London Requires improvement locations, including other service types and inactive records. It is broader than the 115 active homecare locations in the sample. The current database contains 122 London homecare RI locations, of which 115 are active. The 12-month effective-date query returns zero rating events for both the broad and homecare cohorts, subject to the NULL-date limitation above.

## Exact 115-location sample

Matched the IDs in `output/pdf/london-homecare-ri/source-records.json` against production, rather than assuming the broad query represented the sample.

| Measure | Result |
|---|---:|
| Matched locations | 115 |
| Distinct provider IDs | 113 |
| Stored rating-publication date present | 115 |
| Publication later than stored inspection date | 106 |
| Missing inspection date but publication present | 9 |
| Stored publication within the last 12 months | **0** |
| Latest stored publication | **26 April 2024** |
| Latest stored inspection | 28 November 2023 |

Publication years: 2018: 1; 2019: 3; 2020: 2; 2021: 13; 2022: 34; 2023: 58; 2024: 4. There are 112 recently observed rating ledger rows across 112 of these locations, but none is a recognised grade-to-grade pair and none has a recent effective date. Those observed rows do not turn the sample into a recent-change pack.

The legacy date-column criticism is supported: 106 rows have later publication dates and nine gain a usable publication date. But a publication date alone establishes publication, not a change from a prior grade. Rebuilding the trigger from these dates would not create a 2025/2026 trigger list.

A representative [official CQC page for Elegant Excellency](https://www.cqc.org.uk/location/1-13135350550/reports) shows a report published on 26 April 2024, agreeing with the newest stored publication in the sample. It identifies the inspection as 23 November 2023, illustrating that the legacy stored inspection field also needs careful date semantics. The web retrieval is a cached page, not a same-day independent recheck of all 115 records. Do not infer from this spot-check that all records have no newer official assessment. Separating genuine CQC lag from mirror/extraction lag across the whole cohort still requires current, record-level source checks.

## Is there enough measurable supply for a registration-focused brief?

Recent-effective `new_registration` rows, joined to current active locations, using a 90-day window:

| Scope | Events / locations | Distinct provider IDs | Provider IDs with at least one event carrying URL, snapshot hash and effective date |
|---|---:|---:|---:|
| London homecare | 36 / 36 | 35 | **21** |
| England social-care subset | 428 / 428 | 302 | **147** |

These are current database counts, not newly opened companies, verified sales leads, independent legal groups, willingness to buy or paid opportunity outcomes. Completeness of the three metadata fields is a preliminary screen, not independent source validation. Missing evidence may be recoverable, but cannot be counted as accepted customer output before review.

The London scope clears 25 on a naive distinct-provider count but fails 25 under that metadata screen. The wider social-care scope has enough preliminary candidates to test a 25-provider brief without inventing rating-change events. The original rule “fewer than 25 even nationally means drop the product” is too strong when the rating ledger is undated. The defensible rule is: promise a size only after the named scope has enough independently accepted, provider-deduplicated candidates; otherwise quote a smaller explicit scope/size or decline that order.

## Code and readiness assessment

- **Raw source dependency is confirmed at the observed served release.** GitHub source at `b2f519aa8aaebe33197076bd8f2fed6f60a56595`, as well as the local checkout, still has `_LOCATIONS_SNAPSHOT = _REPO_ROOT / "_locations_detail.ndjson"` and a file-existence check. The module itself says the approximately 734 MB file is absent from the serverless bundle. The expected local locations file is absent; the expected provider file is present, dated 24 February 2026. This verifies the configured paths and source code, not an exhaustive search of the Mac or inspection of deployed filesystem contents. Production Postgres exists; the Brief's production source adapter is what is missing.
- **PDF and CSV are confirmed; XLSX is absent from this fulfilment path.** `generate_pack` returns PDF bytes and CSV text; upload/delivery handles those formats. `/pricing/territory` promises CSV and Excel, while the other brief page uses CSV or Excel. Align the contract with accepted output or implement and validate a workbook before making that promise.
- **“Organisations” currently means ranked location rows in the generator.** It builds one candidate per location and slices `candidates[:shortlist_target]`; it does not deduplicate provider IDs. The 115-location sample itself covers 113 provider IDs. Provider deduplication or an explicit location-level promise is required. Provider IDs also do not resolve all legal ownership groups.
- **Deterministic source windows are not freshness acceptance.** The generator anchors its window to the newest date in the snapshot. An old snapshot can therefore produce reproducible output without being current against the calendar. Current-source checks remain separate.
- **The old “both jobs failing today” statement is superseded.** Latest scheduled `main` [Production Smoke](https://github.com/sapopo93/caregist/actions/runs/36825634983) was successful, created 1 October at 06:36 UTC. Latest scheduled `main` [Freshness Watchdog](https://github.com/sapopo93/caregist/actions/runs/36851829296) was successful, created 1 October at 10:52 UTC. The two preceding scheduled runs also passed for each. These workflow conclusions are not independent commercial gate approval.
- **The old freshness/poll figures are not today's figures.** Today's live probes show fresh reconciliation, while checkout remains false, 15 completed seven-day polls against 24 required, and delivery disabled. Scope, terms, source semantics, artefact acceptance and end-to-end paid delivery remain separate requirements. Do not reuse the September 12 percentages as current observations.

Source evidence: `territory-live-source-check.json` contains the served SHA, hashes, links and line excerpts; `territory-workflow-checks.json` contains workflow IDs and conclusions. Local branch HEAD differed from served SHA, which is why the key runtime findings were checked against that served release too.

## Commercial consequence and next bounded step

Keep monitoring first, Brief second and a buyer-funded licensed feed third as product families in the wider research, but withdraw any inference that the Brief is presently ready to generate money automatically. A £745 catalogue price does not establish immediate executable fulfilment or repeat demand.

A proposed registration-focused scope line is: **“Newly registered care locations in your agreed territory, grouped by provider and prioritised for research, with source dates and evidence.”** It requires acceptance of the evidence, scope and delivery path before use as a live sales claim. The system can rank and render; a reviewer still checks source, scope, count and output. Registration does not prove a buyer needs a supplier or is newly operating.

For the rating-change edition, the next bounded step is to reconstruct and independently verify publication-dated, comparable before/after rating history from authoritative reports. Do not fill effective dates from ingestion timestamps. For the registration-based Brief, first freeze and independently review a sufficiently large candidate set for one named scope. Then specify the Postgres input contract, provider deduplication, calendar freshness and actual PDF/CSV or workbook promise before building the adapter. No adapter, branch, source backfill, customer sample rebuild or release gate was changed in this check.
