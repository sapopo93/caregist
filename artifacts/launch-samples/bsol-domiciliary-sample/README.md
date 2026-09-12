# Birmingham and Solihull domiciliary care sample

**SAMPLE — NOT VERIFIED. Built from repository snapshot data for pre-test use only. Not for client delivery until the CQC week-1 data path gate passes.**

Generated on 2026-09-08. The underlying directory rows carry a common last-updated timestamp of 2026-03-28 01:04:17, recorded here as the observation date 2026-03-28.

## What is included

- `bsol-domiciliary-dataset.csv`: 371 active location records classified with the source service type `Homecare Agencies`, comprising 315 in Birmingham and 56 in Solihull.
- `shortlist-25-50.csv`: 40 locations ranked first by registration date, then by the number of active homecare locations sharing the same provider ID in this territory snapshot. Every reason states its source row and avoids inferring a vacancy or staffing need.
- `executive-brief.md`: a recruitment and staffing buyer brief based on the same rows.
- `build_sample.py` and `build.log`: deterministic build and verification route.
- `pre-test-kit/`: drafts and templates for Henry. Nothing in the kit sends or creates a live record.

## Provenance

Primary source: `/Users/user/CareGist/directory_providers.csv`, itself labelled `CQC API v1`. Rows qualify only when `local_authority` is Birmingham or Solihull, `status` is `ACTIVE`, and the pipe-separated `service_types` field contains the exact label `Homecare Agencies`.

`cqc_data_quality_report.md` was reviewed for snapshot limitations but does not supply rows to these CSVs. `_providers_detail.ndjson`, `_providers_list.ndjson`, and `provider_groups.csv` were inspected but were not needed to support the exported row-level claims.

## Known gaps

- This is a repository snapshot, not a current CQC refresh. It has not passed the governed week-1 data-path gate.
- The snapshot contains current ratings but no rating-change history, so the sample makes no rating-movement claim.
- It does not contain a verified closure-event series. Only active rows are included.
- A shared provider ID supports a location-count observation, not a claim of recent expansion, common ownership beyond the identifier, staffing demand, vacancy, budget, or buying intent.
- The source does not distinguish domiciliary care from every other activity at a mixed-service location. Inclusion means the location carries `Homecare Agencies` among its service types.
- Contact fields are incomplete. Blank phone, email, website, rating, inspection, or address fields remain blank. Nothing was enriched or invented.
- Local-authority labels and service classification are accepted as stored in the repository and have not been rechecked against live CQC records.

## Rebuild and verify

From the repository root:

```bash
python3 artifacts/launch-samples/bsol-domiciliary-sample/build_sample.py
python3 artifacts/launch-samples/bsol-domiciliary-sample/build_sample.py --verify
```

The verifier checks every exported dataset row and shortlist evidence pointer against the cited source line, then checks shortlist ranks, qualification rules, observation dates, and stated aggregate location counts.
