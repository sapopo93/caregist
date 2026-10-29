# CareGist rating audit — 22 October 2026

**Verdict: PARTIAL; source defects found. No release or commercial approval.**

The 30-location targeted sample reproduces the live implementation, but does not establish current website accuracy. Search displays and positive filters follow the deployed API-first/file-fallback rule for **30/30** sampled IDs; the file-source label appears on **20/20** file-backed cards and **0/10** other cards. CQC website comparison finds **18 current numerical matches, 5 numerical mismatches, 2 current/inherited-context exceptions, and 5 pages without a numerical location-level overall rating**. No page was inaccessible. The two contextual cases are inconclusive as to the correct current rating and must not be counted as numerical matches or silently resolved by choosing either source.

This deliberately stratified sample includes every known conflict. It is not a random sample of the whole database, and its match fractions must not be presented as a whole-database accuracy estimate.

## Evidence and selection

Observation window: see `requests.json`, `identity-api-requests.json` and the per-row timestamps in `results.json`/`audit.csv` (UTC; London was UTC+1). The database snapshot was read at 20:42:15 UTC / 21:42:15 BST. Production frontend health reports **c50d07e63bd04bd7834d3912fe9a4cc52547f13d**, the merge commit of PR #122. Source files under `source/` were fetched at that exact commit, not read from the older, dirty checkout (HEAD 7ad6471). PR #122 itself labels search cards; earlier source-selection changes are present in its release tree.

`select_sample.py` records the SQL. In a read-only, repeatable-read transaction, select ACTIVE records with a blank API rating and a file rating, order by `md5('caregist-rating-audit-2026-10-22:' || id), id`, and take five per numerical category. Include all five ACTIVE numerical API/file conflicts ordered by ID. Take five ACTIVE records with blank stored API rating and no file overall rating using the same seeded order. No duplicate IDs or substitution after seeing results. Reproduction against a later mutable database can change the population; `sample.json` freezes this population and selection.

The queried database is the existing `.env` database, corroborated against live search for all 30 records and live CQC API location IDs for all 30. Stripe Projects' separately named `production-db` connection was inspected read-only and lacks `file_overall_rating`; it cannot be assumed to be the live directory database. No credentials are included in this packet. The database-endpoint mapping warrants a separate operational check; this audit does not claim an independently verified hosting configuration map.

Snapshot totals: **57,196 ACTIVE**, of which **32,060** have a file rating; **101 INACTIVE** records have a file rating. The original file contains **32,161** unambiguous numerical location-overall ratings. Active file comparisons: **23,375 agree + 8,680 API blank + 5 conflict = 32,060**. File-backed split remains 6,474 Good, 1,735 Requires improvement, 330 Outstanding, 141 Inadequate. These are observations, not a rerun of the importer. Differences from the supplied 57,200/29-inactive handoff are not explained by this audit.

The exact original `ratings.ods` was recovered locally and copied into `source/`. SHA-256 **aba66fd8ca207828a4f6325e7329d98eec3b82aee12a0bfdbceddd58da0c59cd** matches every sampled stored provenance hash. Re-parsing verifies all 25 sampled file values and publication dates and absence of an accepted overall row for the five unrated records. The live source label claims **1 Oct 2026**; ODS modification metadata says **2 Oct 2026 15:11:34Z**, and CQC's data page labels its ratings download **2 October 2026**. Modification/download date does not establish the file's data cutoff. **The 1 October cutoff is not independently verified**; do not turn the hard-coded label into source evidence. File publication dates in `audit.csv` are dates of individual ratings, not the file edition date.

## Results by stratum

| Stratum | Count | Current numerical matches | Numerical mismatches | Context exceptions | No numerical overall visible |
|---|---:|---:|---:|---:|---:|
| File-backed Good | 5 | 5 | 0 | 0 | 0 |
| File-backed Requires improvement | 5 | 5 | 0 | 0 | 0 |
| File-backed Outstanding | 5 | 4 | 0 | 1 | 0 |
| File-backed Inadequate | 5 | 4 | 1 | 0 | 0 |
| All API/file conflicts | 5 | 0 | 4 | 1 | 0 |
| Blank stored API + absent file overall | 5 | 0 | 0 | 0 | 5 |
| Total | 30 | 18 | 5 | 2 | 5 |

Among the 23 records with a current numerical website overall rating, 18/23 (78.3%) match. Including the five no-numerical-overall observations gives 23/30 consistent current-state observations (76.7%), with the two contextual exceptions explicitly excluded from matches. Neither fraction estimates national accuracy.

## Exact exceptions

| Location ID / name | Live display | File rating / publication | CQC website observation | Cause / interpretation |
|---|---|---|---|---|
| [1-125730630 — Welcome House - The Chestnuts](https://www.cqc.org.uk/location/1-125730630) | Inadequate | Inadequate / 25 Sep 2025 | Requires improvement / 13 Oct 2026 | Website update after the claimed file cutoff. Live API remains blank. Snapshot freshness gap, not evidence that the fallback SQL malfunctioned. |
| [1-152721284 — St Stephens Nursing Home](https://www.cqc.org.uk/location/1-152721284) | Good | Requires improvement / 20 May 2026 | Requires improvement / 20 May 2026 | Live API still returns Good / 16 Jul 2019. API-first precedence overrides newer file and website evidence. |
| [1-22160036426 — Irchester 170](https://www.cqc.org.uk/location/1-22160036426) | Outstanding | Good / 11 Mar 2026 | Good / 11 Mar 2026 | Live API returns Outstanding / 7 Mar 2018, with previous organisation ID 1-123630928 in key-question evidence. API-first precedence selects older/inherited evidence. |
| [1-390976877 — Althorp Grange](https://www.cqc.org.uk/location/1-390976877) | Inadequate | Requires improvement / 11 Dec 2025 | Requires improvement / 11 Dec 2025 | Live API still returns Inadequate / 28 Feb 2024. Same precedence defect. |
| [1-552527797 — The Chesser Surgery](https://www.cqc.org.uk/location/1-552527797) | Good | Requires improvement / 9 Jan 2025 | Requires improvement / 5 Mar 2025 | Live API still returns Good / 10 Nov 2016. Same precedence defect; file and website publication dates also differ despite agreeing numerically. |
| [1-16491295796 — Tillingham Medical Centre](https://www.cqc.org.uk/location/1-16491295796) | Outstanding, file label | Outstanding / 24 Aug 2018 | No current overall; provider changed, registered 26 Jul 2023, not inspected yet | Current-provider mismatch/context exception. Previous-provider inheritance is plausible but not proven by following the old profile in this audit. Do not call Outstanding a verified current inspection rating. |
| [1-19886383752 — The Check House](https://www.cqc.org.uk/location/1-19886383752) | Outstanding, no file label | Good / 7 May 2026 | Not inspected yet under current provider; explicitly inherited Outstanding / 8 Jun 2018 | API's Outstanding is confirmed only as historic inherited evidence. File's newer Good conflicts with this page. Correct current state remains unresolved; neither wholesale API nor wholesale file precedence is justified. |

These cases represent **five numerical differences and two semantic exceptions**, not seven simple wrong-value records. Raw HTML, browser accessibility evidence for Check House, live API responses, and rating/report dates are included. No upstream-cause claim beyond that evidence is made.

## The five unrated cases

All five have no numerical location-level overall rating on the captured CQC page and no accepted overall row in the file. This does not prove CQC publishes no information about them.

- `1-12566526711`, Candela Healthcare: CQC says not inspected yet.
- `1-29650851551`, NEAD Support: CQC says not inspected yet, registered 10 Sep 2026.
- `1-199649069`, Belle Vale Dental Centre: inspection report published 13 Dec 2013; a report can exist without a numerical rating.
- `RHARA`, Nottingham University Hospital: page directs readers to provider-level community/mental-health inspection reports.
- `1-5588555895`, The Doctors Laboratory: report published 25 May 2022; live API explicitly says **Inspected but not rated**, although stored `overall_rating` is blank. This is consistent with no numerical rating, but loses useful status in the stored/displayed representation.

## Territory Brief source trace at the deployed release

| Surface | Source and code evidence | Do file-backed ratings reach it? |
|---|---|---|
| Search display and positive rating/segment filters | `frontend/lib/directory-query-clauses.ts`: `RECONCILED_RATING_SQL`, `RATING_SOURCE_SQL`; `directory-db.ts`: `buildWhereClause`, `buildSearchSql` | Yes: fallback only if API has no numerical rating. All 30 sampled positive-filter pages match that rule. |
| Public Brief coverage enquiry | `frontend/app/api/territory/coverage/route.ts` -> `getTerritoryScopeCoverage` -> `buildWhereClause` -> reconciled opportunity predicates | Yes for rating-based scope membership. This is a source trace, not a live coverage-endpoint exercise or delivered-count proof. |
| Paid generator source | `api/services/territory_brief_delivery.py`: `_snapshot_paths`, `generate_pack` -> `generate_territory_opportunity_brief` | No. Reads `_locations_detail.ndjson` and `_providers_detail.ndjson`; no join to file-rating columns. Deployed source comments warn the large snapshot is not bundled for serverless generation. Actual runtime file availability is not tested here. |
| Brief shortlist/current-rating fields and narrative | `territory_brief.py`: currentRatings extraction near lines 1102–1108, `_reason` call, `_provider_group_event` (line 940) | No. `current_rating` comes from API snapshot `currentRatings.overall`; file-only ratings cannot populate it. |
| Brief rating evidence appendix and freshness decisions | `_current_rating_evidence` (line 1286), `_evidence_coverage` (line 1299), `rating_date_coverage` | No. API snapshot rating/report date only. No file provenance/date bridge. This internal evidence coverage differs from the public enquiry count. |
| Brief PDF and CSV | `territory_brief_render.py` uses `o.current_rating` and evidence coverage; `brief_to_csv` exports `org.current_rating`, publication date and freshness | No. Outputs inherit the generator's omission. JSON serialization uses the same object. No complete customer PDF/CSV was generated or approved by this audit. |
| Rating-change signals | `tools/generate_radar_territory_sample.py::_rating_sequence` reads historicRatings/currentRatings | No file reconciliation. A single snapshot rating must not be manufactured into a rating-change event. |

`brief-reader-reproduction.json` executes the exact deployed `_current_rating_evidence` function against the 30 saved live API payloads with file fields added. It returns **no rating for all 20 file-backed examples**, demonstrating that merely carrying file fields alongside the API payload does not repair the deployed reader. This is a bounded reader reproduction, not a complete Brief-generation test.

The uncommitted local `territory_brief_source.py` and changed delivery/generator files are not present at the deployed commit. They must not be cited as live fixes. They also require their own review before use.

## Single next bounded fix

**Create a provenance-aware resolved-current-rating input contract for the Territory Brief and use it consistently in its current-state tables, narrative, evidence appendix, PDF/CSV/JSON and rating-based scope decisions.** Preserve API and file evidence separately; include rating date, source hash/edition and current/inherited/unresolved status. Do not simply copy the current directory API-first CASE expression into the Brief: this audit disproves its freshness assumption in four conflicts. Do not blindly prefer the file either: Check House and Tillingham require unresolved/inherited handling, while Chestnuts requires fresher evidence.

Acceptance: the 20 file-backed fixtures retain their file value/date/provenance; the four older-API conflicts cannot silently override newer verified evidence; inherited/unresolved fixtures remain qualified and cannot be ranked as verified current inspections; post-snapshot evidence remains visibly newer; PDF, CSV, JSON and coverage decisions agree on the same accepted edition; a file observation is never labelled a new rating-change event. Prepare and test locally, then freeze for Grok retest and an independent approved-provider reviewer. No production write or gate opening is authorised by this recommendation.

## Claim-to-evidence quality gate

| Promise / intended reader | Source / observable evidence | Pass condition | Result |
|---|---|---|---|
| Founder can reproduce 30 distinct records | `select_sample.py`, `sample.json` | 20 stratified + all 5 conflicts + 5 blanks, unique active IDs | PASS for frozen sample |
| Each comparison has ID, source/date and timestamp | `results.json`, `audit.csv`, original ODS, two request ledgers | Each selected ID joins its live API ID, CQC URL and live card; 25 file values/dates match source | PASS; file cutoff explicitly unverified |
| Live search behaviour is honestly distinguished from source accuracy | 90 initial page responses; rendered browser search check; 60 API/profile responses | 30 expected badges/filter membership; 20 labels; exceptions classified separately | PASS for checked behaviour; current accuracy PARTIAL |
| Brief source claim is tied to deployed code | `source/` at c50d07e; bounded reader reproduction | Trace tables/narrative/coverage/exports without claiming full generation | PASS for trace; full customer output NOT VERIFIED |
| Reviewer receives a frozen, self-contained packet | `MANIFEST.sha256`, raw HTML/text/JSON/ODS, report and audit scripts | Hash verification and complete exception evidence | See manifest validation |

Adversarial checks: distinguish scripts from displayed server HTML (resolve streamed fragments); never count a raw label-string count as card count; keep two contextual cases outside numerical comparisons; preserve 2018/2019 API dates rather than assuming live API means fresh rating; keep uninspected, inspected-but-not-rated and provider-level reports distinct; confirm all live API IDs; check every file-backed label and every positive filter result. Automated assertions are in `finalise_results.py`.

Limits: browser rendering was checked for one representative search and the Check House CQC page; the other records use parsed server-rendered HTML and live API responses, not 30 screenshots. No negative-filter matrix, whole-database website audit, old-profile investigation, runtime Brief generation, purchase/delivery test, backend release identity proof, external reviewer run or commercial acceptance was performed. No production data, gates, code, merge or deployment was changed. This is the producer's audit; independent review remains pending. DeepSeek is prohibited under current AGENTS.md, notwithstanding older warroom text naming it.
