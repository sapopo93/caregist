# Bounded source-to-deliverable verification

8 September 2026. PASS for this local September snapshot pack. This is not production pipeline reconciliation, commercial release approval or proof of live monitoring.

Primary files and exact download URLs, retrieval timestamps, byte sizes and SHA-256 hashes are recorded in [pack-data.json](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/pack-data.json). Both CQC downloads returned HTTP 200. Monthly ODS converted using LibreOffice to the retained CSV in `source/converted/`.

- Monthly active-locations edition, 1 September: 57,069 unique location rows. SHA-256 `1b64024445823e2e53c329c47b44d69831170df12b42bb2a300958cc8d98aa93`.
- Weekly directory edition, 2 September: 57,085 unique location rows. SHA-256 `5b5ef41bafcedd8243f9d6310fae31d2fcbdb361b98f162d7d35227b5292b592`.
- Selection: Birmingham or Solihull local authority, domiciliary service flag Y, dormant flag N. Result: 353 locations, 329 provider IDs. 297 Birmingham and 56 Solihull.
- All 353 selected location IDs, provider IDs and authorities match the weekly directory. National totals differ across editions. No national reconciliation or closure conclusion is claimed.
- Shortlist: 15 providers with several local locations and 10 remaining providers ordered by most recent qualifying registration. 25 distinct provider IDs. Criteria are illustrative for a staffing buyer.
- 25 representative CQC pages returned HTTP 200 and contained the matching location name with no detected archived notice. Saved HTML and hashes are retained in `source/location-pages/` and `pack-data.json`. This validates page access and name matching, not every field or every location.
- Final workbook contains three sheets, 378 source-link formulas, zero saved error cells and checked summary totals. Both delivered CSVs match every field in `pack-data.json`.
- PDF: four pages, text extraction passed, all four rendered pages visually inspected. Workbook views from all sheets inspected.

The initial artifact-tool export left HYPERLINK calculation errors despite its generic error scan returning zero matches. LibreOffice recalculation fixed the saved file. The verifier now rejects every Excel cell marked as an error. Do not substitute the earlier inspect log for this check.

The artifact renderer also recalculates unsupported HYPERLINK functions on import. Final link-column previews therefore use a display-only copy with the exact friendly strings checked against final XLSX caches. The delivery workbook retains its working formulas and was not exported from that preview copy. All 378 saved formula targets and cached display values pass the verifier.

Reproduce with `build_evidence.py`, `build_workbook.mjs`, `build_pdf.py`, then `verify_pack.py` in this directory, using the bundled Node/Python runtimes. `build_workbook.mjs` recalculates the export with `/opt/homebrew/bin/soffice`. The latest machine result is [qa/verification.json](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/qa/verification.json).

Source guidance: [CQC Using CQC data](https://www.cqc.org.uk/about-us/transparency/using-cqc-data). Published files have update delays. Raw source files stay in the evidence directory. Buyer exports omit named managers and personal contact fields.
