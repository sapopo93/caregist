# CQC reconciliation + unrated classification - 2026-09-20

Generated `2026-09-20T04:21:14.646634+00:00`. Read-only investigation: SELECTs + public CQC API GETs only; no DB writes, no commits, no repo edits.

Evidence files: `2026-09-20-reconciliation-detail.json`, `2026-09-20-unrated-classification.json` (this .md is a readable summary; every number below is traceable to one of them).

## Headline: the DB is one CQC weekly publication behind

- Newest source **available**: the **2026-09-16** directory CSV - sha256 `bed9e95a1701...`, **57,127** location ids (re-downloaded and re-hashed; an independent copy at `/tmp/dir16.csv` hashes to the same value).
- Newest snapshot the DB has actually **validated**: the **2026-09-09** directory - sha256 `cf2e7bc20493...`, **57,151** locations, ingested by batch `b84cb3de` completed `2026-09-16T12:00:07.325481+00:00`.
- **`newest_snapshot_covered` = false**: no `reconciliation_batches` row references the 2026-09-16 checksum, so **validated coverage stops at 2026-09-09 while a newer 2026-09-16 source exists** (7-day gap).
- Measured against the *newer* source, the DB carries **127 ACTIVE rows CQC no longer lists**, and **67 of them are confirmed DEREGISTERED by live CQC while still served as ACTIVE**.
- `only_in_source` = **0** - the DB is missing no snapshot rows at all; the divergence is status-side.

## 1. Source snapshot

- URI: `https://www.cqc.org.uk/system/files/2026-09/16_september_2026_CQC_directory.csv`
- Published: **2026-09-16** | Retrieved: **2026-09-20T04:13:50Z** | Unique location ids: **57,127**
- sha256 `bed9e95a1701ade0c4933bdf3acda7a9c4c94e3940a19ad698575a05a66eecb0` - verified by re-download (18,959,346 bytes) plus `shasum -a 256`
- Command: `curl -sS -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" -o cqc_directory_2026-09-16.csv "https://www.cqc.org.uk/system/files/2026-09/16_september_2026_CQC_directory.csv" && shasum -a 256 cqc_directory_2026-09-16.csv`

## 2. Does `care_providers` hold locations or providers?

**Answer: CQC *locations*, one row per location - the table name is misleading.**

- CQC directory CSV carries TWO identifier columns: 'CQC Location ID (for office use only)' (57,127 unique values, one per row) and 'CQC Provider ID (for office use only)' (37,088 unique values across 57,127 rows).
- care_providers.id (PK, varchar(20)) intersects the CSV LOCATION ID column on 57,127/57,127 values (100%); it intersects the CSV PROVIDER ID column on 0 values.
- care_providers.provider_id holds 38,024 non-NULL values of which 37,085 match CSV PROVIDER IDs and 0 match CSV LOCATION IDs -> provider_id is the parent-organisation reference (nullable, many locations per provider).
- 57,066 intersecting rows are DB ACTIVE and 61 are DB INACTIVE; there are 37,088 distinct providers vs 59,030 DB rows (~1.6 locations per provider) -> one DB row per CQC LOCATION, not per provider.
- 1,831 DB ids (1,774 ACTIVE + 57 INACTIVE) use CQC's legacy short location-id form (e.g. 'RHAR1', 'RP102'); 1,769 such short ids appear in the CSV location-id column. The `1-XXXXXXXXXXX` shape named in the task describes 57,199 of 59,030 DB rows and 55,358 of 57,127 snapshot rows; it is the modern CQC location-id shape, not a provider-id shape.

care_providers stores CQC LOCATIONS (one row per location). The table name is misleading; provider_id is the parent provider key.

So "25,753 ACTIVE care providers without a rating" is really 25,753 ACTIVE **locations**.

## 3. Identifier / status reconciliation

| Measure | Count |
|---|---:|
| `care_providers` total rows | 59,030 |
| DB status ACTIVE | 57,193 |
| DB status INACTIVE | 1,837 |
| Snapshot unique location ids (2026-09-16) | 57,127 |
| **overlap** (snapshot id present in DB, any status) | **57,127** |
| ... of which DB ACTIVE | 57,066 |
| ... of which DB INACTIVE | 61 |
| **only_in_db_active** (DB ACTIVE, id absent from snapshot) | **127** |
| **only_in_source** (snapshot id with no DB row) | **0** |
| **source_but_db_inactive** (in snapshot, DB non-ACTIVE) | **61** |

Arithmetic check: 57,066 + 127 = **57,193** DB ACTIVE, and 57,066 + 61 = **57,127** snapshot ids.

## 4. Divergence classification (live CQC API, all 188 ids - no sampling)

Each id fetched with `GET {DEFAULT_BASE_URL}/locations/{id}` + `api_headers(get_api_key())`; per-id raw `registrationStatus` / `registrationDate` / `deregistrationDate` live in the JSON's `classification.per_id`. 0 rate-limit errors, 0 `api_error`, 0 `api_404_or_gone`.

### 4a. `only_in_db_active` (127 ids)

| Class | Count | Reading |
|---|---:|---|
| `confirmed_deregistered_but_active_in_db` | **67** | **CONFIRMED DEFECT** - CQC says not Registered; the DB still publishes it as ACTIVE |
| `registered_after_snapshot` | 32 | legitimate timing difference (registered on/after 2026-09-16) |
| `registered_on_or_before_snapshot_but_absent` | 28 | snapshot publication lag (legitimate) |

Deregistration dates of the 67 confirmed-defect locations:

| deregistrationDate | ids |
|---|---:|
| 2026-09-08 | 18 |
| 2026-09-10 | 18 |
| 2026-09-09 | 10 |
| 2026-09-14 | 10 |
| 2026-09-11 | 9 |
| 2026-09-16 | 3 |
| 2026-08-10 | 1 |
| 2026-09-12 | 1 |
| 2026-09-15 | 1 |

### 4b. `source_but_db_inactive` (61 ids)

| Class | Count | Reading |
|---|---:|---|
| `registered_on_or_before_snapshot_but_absent` | **57** | API **Registered** and the directory still lists the location, but the DB row is INACTIVE - opposite-direction status error |
| `confirmed_deregistered_but_active_in_db` | 4 | API says Deregistered, so the DB's INACTIVE status is right and the snapshot row is merely stale |

## 5. Reconciliation bookkeeping

| batch id | status | created_at | source published | sha256 (prefix) | locations | active before -> after | deactivated | error |
|---|---|---|---|---|---:|---|---:|---|
| `b84cb3de` | completed | 2026-09-16T07:42:01.712336+00:00 | 2026-09-09 | `cf2e7bc20493` | 57,151 | 57157 -> 57151 | 14 |  |
| `ebe41652` | completed | 2026-09-14T15:21:52.560987+00:00 | 2026-09-09 | `cf2e7bc20493` | 57,151 | 57178 -> 57150 | 50 |  |
| `66b53f7f` | failed | 2026-09-13T11:11:28.745698+00:00 | 2026-09-09 | `cf2e7bc20493` | 57,151 | 57181 -> null | 0 | Workflow ended before every shard completed |
| `1cc6ed32` | failed | 2026-09-04T20:46:28.661934+00:00 | 2026-09-02 | `5b5ef41bafce` | 57,085 | 57191 -> null | 0 | Workflow ended before every shard completed |
| `7fac8994` | failed | 2026-09-03T13:20:32.792960+00:00 | 2026-09-02 | `5b5ef41bafce` | 57,085 | 57087 -> null | 0 | Workflow ended before every shard completed |
| `56a11f0f` | failed | 2026-08-12T17:56:34.820782+00:00 | 2026-08-12 | `6d2641bdfb4d` | 57,060 | 58412 -> null | 0 | Workflow ended before every shard completed |
| `c6e7d7fa` | failed | 2026-08-11T03:35:50.539765+00:00 | 2026-08-05 | `98fdcfa13ad6` | 57,025 | 57816 -> null | 0 | Workflow ended before every shard completed |
| `709da422` | failed | 2026-08-11T03:27:29.290033+00:00 | 2026-08-05 | `98fdcfa13ad6` | 57,025 | 57816 -> null | 0 | Workflow ended before every shard completed |
| `6c79a8a4` | failed | 2026-08-10T22:57:42.397301+00:00 | 2026-08-05 | `98fdcfa13ad6` | 57,025 | 56742 -> null | 0 | Workflow ended before every shard completed |
| `f9d1d309` | failed | 2026-08-10T22:50:05.122311+00:00 | 2026-08-05 | `98fdcfa13ad6` | 57,025 | 56742 -> null | 0 | Workflow ended before every shard completed |

Failed runs: `66b53f7f` (2026-09-13T11:11:28.745698+00:00) - `Workflow ended before every shard completed`; `1cc6ed32` (2026-09-04T20:46:28.661934+00:00) - `Workflow ended before every shard completed`; `7fac8994` (2026-09-03T13:20:32.792960+00:00) - `Workflow ended before every shard completed`; `56a11f0f` (2026-08-12T17:56:34.820782+00:00) - `Workflow ended before every shard completed`; `c6e7d7fa` (2026-08-11T03:35:50.539765+00:00) - `Workflow ended before every shard completed`; `709da422` (2026-08-11T03:27:29.290033+00:00) - `Workflow ended before every shard completed`; `6c79a8a4` (2026-08-10T22:57:42.397301+00:00) - `Workflow ended before every shard completed`; `f9d1d309` (2026-08-10T22:50:05.122311+00:00) - `Workflow ended before every shard completed`.

Shards for the two newest batches:

| batch | shards | statuses | processed/expected | fetch_failures | clean_failures |
|---|---:|---|---|---|---|
| `b84cb3de` | 8 | {'completed': 8} | 57,151/57,151 | 0 | 0 |
| `ebe41652` | 8 | {'completed': 8} | 57,151/57,151 | 0 | 0 |

## 6. What the unrated ACTIVE population actually is

Measured count of ACTIVE rows with no published overall rating: **25,753**

```sql
SELECT id FROM care_providers WHERE status = 'ACTIVE' AND (overall_rating IS NULL OR btrim(overall_rating) = '')   -- COUNT(*) = 25753
```
Breakdown of *how* the blank is stored: `overall_rating IS NULL` = 0; `btrim(overall_rating) = ''` = 25,753. The DB stores the **empty string**, not NULL - which is why the predicate covers both.

Denominators: ACTIVE 57,193; rated ACTIVE 31,440; unrated ACTIVE 25,753 (45.03% of ACTIVE); table total 59,030.

### 6a. Sample-based classification (n=300, source evidence only)

```sql
SELECT id FROM care_providers WHERE status = 'ACTIVE' AND (overall_rating IS NULL OR btrim(overall_rating) = '') ORDER BY random() LIMIT 300
```

| Class | Sample n | % of sample | Population estimate | 95% Wilson CI (ids) |
|---|---:|---:|---:|---|
| `has_published_rating_now` | 0 | 0.0% | 0 | 0 - 326 |
| `sentinel_not_a_rating` | 0 | 0.0% | 0 | 0 - 326 |
| `no_current_ratings_but_historic_overall` | 96 | 32.0% | 8,241 | 6,947 - 9,652 |
| `never_rated_no_historic_overall` | 204 | 68.0% | 17,512 | 16,101 - 18,806 |
| `api_404_or_gone` | 0 | 0.0% | 0 | 0 - 326 |
| `api_error` | 0 | 0.0% | 0 | 0 - 326 |

**Sample-based estimates (n=300) - never full-population truth.** The sample counts are exact; the population columns are extrapolations with 95% Wilson score intervals over a 25,753-row population.

- **0/300 had a currently published overall rating** (`currentRatings.overall.rating` present and not a sentinel) -> **no ingestion omission detected**. The Wilson upper bound on a 0/300 cell is 1.26% (326 ids), so a small omission slice is not excluded - it is simply not evidenced.
- **0/300 returned a CQC sentinel string.** Sentinels are stored verbatim in `overall_rating` and are *not* in this population: `Inspected but not rated` 5,640, `No published rating` 1,644, `Insufficient evidence to rate` 23. `incremental_update.clean_location()` writes `''` only when `currentRatings.overall.rating` is absent.
- Sub-split by API shape: 13 of the 96 historic-class members returned a `currentRatings` object that carries `reportDate`/`serviceRatings` but **no `overall` key** (legitimately unrated, not an omission); the other 83 returned no `currentRatings` at all. All 204 never-rated members returned no `currentRatings`.

### 6b. Owner-supplied worked examples - independently re-verified

| id | DB status | DB `overall_rating` | HTTP | `currentRatings` | `currentRatings.overall` | `historicRatings[].overall.rating` | class |
|---|---|---|---:|---|---|---|---|
| `1-454430341` | ACTIVE | `''` | 200 | **absent** | absent | `Inspected but not rated` | `no_current_ratings_but_historic_overall` |
| `1-459391070` | ACTIVE | `''` | 200 | **absent** | absent | `Requires improvement` | `no_current_ratings_but_historic_overall` |
| `1-4650627138` | ACTIVE | `''` | 200 | present | absent | `Good` | `no_current_ratings_but_historic_overall` |
| `1-4625499825` | ACTIVE | `''` | 200 | **absent** | absent | `Good` | `no_current_ratings_but_historic_overall` |
| `1-495687551` | ACTIVE | `''` | 200 | **absent** | absent | `Good` | `no_current_ratings_but_historic_overall` |
| `1-5442188628` | ACTIVE | `''` | 200 | **absent** | absent | `Requires improvement` | `no_current_ratings_but_historic_overall` |
| `1-545581747` | ACTIVE | `''` | 200 | present | absent | `Good` | `no_current_ratings_but_historic_overall` |

**7/7 confirm class (a)**: DB blank + no `currentRatings.overall` + a populated `historicRatings` overall. Two corrections of detail, however: for `1-4650627138` and `1-545581747` `currentRatings` is **present** (it carries `reportDate`/`serviceRatings` but no `overall` key), so "currentRatings absent" is imprecise - the accurate statement is "`currentRatings.overall` absent". Also `1-454430341`'s only historic overall value is itself the sentinel `Inspected but not rated`, so it is arguably a never-really-rated case rather than a previously-rated one.

### 6c. Full-population internal cross-check (`trusted_event_ledger`)

This is a **measured, full-population** check - not a sample.

- `new_value` / `old_value` are **jsonb**. The absent-destination predicate is `new_value::text = 'null'`; `new_value IS NULL` gives only **4** rows (all `integration_connectivity`) and is the wrong predicate here.
- All-time `rating_changed` events with an absent destination: **24,486** across 0 locations (real-destination `rating_changed` events: 9,810).
- For the 25,753 unrated ACTIVE rows, the **most recent** `rating_changed` event has an absent destination for **23,597** rows, and **0** rows have a most-recent destination holding a real rating value. (23,597 have some `rating_changed` event; the remaining 2,156 have none - never rated.)
- **Conclusion: zero unrated rows have an internal record contradicting the blank rating.** Even the 127 rows that once had a non-null-destination `rating_changed` event were later superseded by an absent-destination event. The blank is consistent with the pipeline's own history, so it is not a lost update.

### 6d. DB-side provenance: reconciliation vs signal sweep

| Last writer | Rows |
|---|---:|
| `last_written_by_reconciliation_run` | 21,650 |
| `last_written_by_signal_poll_run` | 4,103 |

`care_providers` has **no per-row `run_id`**; both the reconciliation detail pass and the signal sweep call `upsert_provider()`, which stamps `updated_at = now()`. Each unrated row's `updated_at` was mapped into the `pipeline_runs` `signal_poll` windows or the `reconciliation_batches` windows. 21,650 were last written inside a reconciliation window, 4,103 inside a `signal_poll` window. Exact last-writer attribution is therefore **inferential**.

## 7. What could NOT be determined

- **Exact per-row last-writer attribution.** No per-row run/source column exists on `care_providers`; the split in 6d is inferred from timestamp windows.
- **A full-population figure for the unrated split.** n=300 gives ranges, not measured totals; the 0-count cells still carry a 1.26% population upper bound.
- **Whether the 2026-09-09 DB snapshot was itself internally complete.** Only the 2026-09-16 snapshot was downloaded and hashed here; the 2026-09-09 file was not re-fetched, so its 57,151-location count is taken from `reconciliation_batches` and its checksum from the batch row (not independently recomputed).
- **Why the 2026-09-16 snapshot was never ingested.** No `reconciliation_batches` row references it and no scheduler evidence was inspected; the cause is out of scope for this read-only pass.
- **CQC's own directory is treated as the authoritative active-location set.** No second CQC source was cross-checked.
