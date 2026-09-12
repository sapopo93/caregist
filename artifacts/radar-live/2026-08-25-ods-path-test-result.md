# ODS Path Test Result — 2026-08-25

Status: `PASSED — LIVE PATH EXISTS AND WORKS`. This supersedes the stale
"no verified live path" stop-rule language recorded on 2026-08-13/2026-08-22.
The stop rule is NOT deleted; it is now re-anchored to verified evidence:
a deliverable digest MUST be compiled from a verified source and recorded as
such before any buyer-facing "current" claim.

Tested by: hermes @caregist (shell-capable agent) on 2026-08-25.
UTC timestamps recorded at execution.

---

## 1. What was tested

CQC's official "Using CQC data" page:
`https://www.cqc.org.uk/about-us/transparency/using-cqc-data`
(last updated 5 August 2026 per henry-proof's independent check).

Files located and downloaded (HTTP 200, browser user-agent, no auth):

| File | Edition | Bytes on disk | Purpose |
|---|---|---|---|
| `2026-08-04_HSCA_Active_Locations.ods` | 04 Aug 2026 | 24,103,499 | Active locations + HSCA start (registration) dates + ratings |
| `2026-08-04_Latest_ratings.ods` | 04 Aug 2026 | 26,949,208 | Latest ratings by location |
| `2026-08-19_CQC_directory.csv` | 19 Aug 2026 | 18,942,208 | Freshest plain-CSV directory (no registration dates) |

All three stored under `/Users/user/CareGist/artifacts/radar-live/`.

Fetch timestamps (mtime on disk, UTC, from `stat` 2026-08-25):
- `2026-08-19_CQC_directory.csv` — 2026-08-25T04:55:49Z
- `2026-08-04_HSCA_Active_Locations.ods` — 2026-08-25T04:55:50Z
- `2026-08-04_Latest_ratings.ods` — 2026-08-25T04:55:51Z

SHA-256 (recorded 2026-08-25):
- `2026-08-04_HSCA_Active_Locations.ods` — `ae87c164209ce6c0b0d7fef2b873dd2a1120f86873ca81e9c271b0a669cdd3f7`
- `2026-08-04_Latest_ratings.ods` — `c074f36c9d94fc51cfbd8bad4bb6069ed84a8d1ab0b7e6e8b7af03cd3a151bce`
- `2026-08-19_CQC_directory.csv` — `dee9bb394fa126ffdcf059e89e6cf2a86b02284b17d025f105a20621ac27540a`

## 2. Parse method

Regex XML parsing of the ODS proved unreliable (merged/covered cells shift
columns). Authoritative parse: LibreOffice headless ODS→CSV conversion
(`soffice --headless --convert-to csv`), then column-indexed reads.

Verified against the Nuffield Health Cheltenham Hospital row
(location id `1-115574419`):
- Provider ID `1-102643516` at column 37
- Provider Name `Nuffield Health` at column 38
- Postcode `GL51 6SY` at column 27
- HSCA start (registration) date at column 1
- Latest rating `Good` at column 13, publication date `29/07/2026` at column 14

## 3. Fresh weekly digest — Gloucestershire (29 Jul – 04 Aug 2026)

Compiled: `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md`
JSON: `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.json`

Provenance:
- Source: `2026-08-04_HSCA_Active_Locations.ods` (official CQC edition)
- Parsed rows: 57,009 active locations (authoritative LibreOffice CSV export)
- Gloucestershire rows: 684
- Window: 2026-07-29 to 2026-08-04 (7 days)
- Events in window:
  - new_registration: 0
  - rating_published: 1 (Nuffield Health Cheltenham Hospital — Good,
    publication date 2026-07-29)

Interpretation (honest, no spin):
- The ODS path WORKS: fresh CQC register data is reachable without auth.
- The weekly digest for Gloucestershire in that specific week has **zero new
  registrations**. A "new registrations" digest will often be sparse in a
  single small county; the product's value proposition must be stated
  truthfully (e.g. "updates, including when there are none") or the territory
  scope widened. This is a real product-shape finding, not a defect.
- The 19 Aug CSV is fresher than the 04 Aug ODS but carries NO registration
  dates (only "Date of latest check" = inspection). Registration events can
  only be compiled from the ODS (monthly cadence) or the CQC API.
- The digest can therefore be promised as "compiled from the current CQC
  register edition" — but buyer-facing wording must NOT change until Henry
  approves the updated sample language. This evidence is the basis for that
  approval, not a substitute for it.

## 4. What this changes

- STOP RULE UPDATE (recorded): "No verified live path" is retired as a
  standalone blocker. Replaced by: "A digest may only be described as current
  when its source edition is a verified CQC public file recorded in
  `artifacts/radar-live/`; otherwise it must be labelled a dated sample."
- The dated February 2026 sample remains valid as a FORMAT sample only.
- Buyer-facing promise upgrade (dated sample → current sample) still requires
  Henry's recorded approval. No buyer has been contacted.

## 5. Remaining evidence gaps (unchanged)

- 11 FIT rows unverified; rows 3–5 of the first five marked PROVISIONAL
  pending independent site checks (see verification artifact).
- CTPS/TPS screening NOT run — correctly pending Henry's outreach-scope signoff.
- No settlement account; no live payment route.
- Invoice layout + ask-to-pay wording drafted for inspection
  (`artifacts/radar-live/2026-08-25-draft-invoice-layout-ask-to-pay.md`),
  not yet approved.
