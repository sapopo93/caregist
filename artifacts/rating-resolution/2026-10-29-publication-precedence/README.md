# Publication precedence amendment — local candidate, contract v2

Supersedes the previous candidate's date-comparison policy. The original frozen packet remains unchanged.

Decision: compare publication dates only between CQC ratings file and CQC website rating evidence. The newest dated publication wins. Undated website evidence can fill a gap but cannot override dated evidence. API ratings and their dates are retained as candidates and fill gaps only when no file/website rating publication exists. Inherited/context conflicts, unsupported statuses and unorderable same-date/undated publication disagreements remain unresolved, with all candidates and provenance retained.

Each accepted rating carries source and publication date through narrative, scope, evidence appendix and PDF/CSV/JSON. Labels say “matches CQC's published rating as of [date]”. Missing publication dates are explicit; an inspection, scoring, retrieval or observation date never supplies a missing publication date. Public scope requires contract v2, so older editions need a separate new evidence import before use. No production import is authorised or performed.

Frozen 30-fixture input: ../2026-10-29/fixtures.json and rating-evidence.json; original source evidence remains artifacts/rating-audit/2026-10-22/. Generated Brief uses the same synthetic Fixture County/provider/registration wrapper documented in the original packet. It is an acceptance artifact, not a delivered customer Brief or a live website check.

Amendment files: api/services/territory_rating.py; api/services/territory_brief.py; frontend/lib/territory-rating-coverage.ts; tests/test_territory_rating_resolution.py. Warroom checkpoint and review-queue documentation refreshed. No checkout/delivery gates, production writes, merges or deployments changed.

Checks: 128 backend tests, 8 isolated local Postgres tests, 9 frontend tests passed; TypeScript check passed. All frozen rating decisions remain unchanged; tests now explicitly prove that even a later API date cannot displace a CQC publication and an undated website cannot displace a dated file. A separate regression proves undated group narrative does not claim an inspection date as a rating publication date.
