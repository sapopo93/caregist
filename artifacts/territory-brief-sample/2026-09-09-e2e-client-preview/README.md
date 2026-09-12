# Territory Opportunity Brief — E2E client preview (dry-run)

**Date:** 2026-09-09 (Europe/London)  
**Mode:** Operator dry-run only. No Stripe, no checkout flag, no env changes, no commit.

## Scope used (CLI Slice-2 generator)

| Field | Value |
|---|---|
| Territory | Birmingham and Solihull (`--kind region`) |
| Service focus | Domiciliary / Homecare Agencies (pre-filtered extract) |
| Buyer framing | Recruitment / staffing (sales sample positioning; not a CLI flag) |
| Window | 365 days (2025-02-21 → 2026-02-20, anchored to newest registration in extract) |
| Shortlist target | 25 |
| Order reference | `dry-run-e2e-2026-09-09` |

## Primary deliverables (new CLI format)

- `territory-opportunity-brief-birmingham-and-solihull.pdf` — executive brief + appendix
- `territory-opportunity-brief-birmingham-and-solihull.csv` — ranked shortlist
- `territory-opportunity-brief-birmingham-and-solihull.json` — structured pack

## Fallback / data note

Full `_locations_detail.ndjson` (~734 MB) is **not present** on this Mac (only `_providers_detail.ndjson` + `_locations_list.ndjson` list stub).  
The CLI pack was generated from a **local extract** built from `directory_providers.csv` (371 ACTIVE Homecare Agencies rows in Birmingham/Solihull; synthetic region name `Birmingham and Solihull` so the combined sales territory is one CLI scope). See `_extract/EXTRACT_README.json`.

## Legacy sales sample (copied, not regenerated)

`legacy-sales-sample/` contains the existing Sep-8 Birmingham/Solihull domiciliary recruitment prototype (4-page PDF, XLSX, shortlist CSV, territory CSV) that a client would historically receive from the manual pack path.

## Safety

`TERRITORY_SELF_SERVE_CHECKOUT_ENABLED` was not touched. No Vercel/Stripe/secrets/git remotes/commits.
