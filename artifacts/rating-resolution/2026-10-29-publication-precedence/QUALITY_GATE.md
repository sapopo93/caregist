# Bounded producer quality gate

| Promise | Observable acceptance evidence | Verdict |
|---|---|---|
| API excluded from newest-publication comparison | API dated 29 October loses to file dated 1 January; API provenance/date retained | PASS |
| Undated website fills gaps only | Dated file defeats undated website; undated website defeats API in a publication gap | PASS |
| Unresolvable conflict candidates retained | Equal-date and undated conflicting publications yield unresolved with both values | PASS |
| Source/date shown without live claim | Shared label and export fields; undated source dates remain null/blank and explicitly unavailable | PASS |
| Narrative never substitutes inspection/scoring dates | Undated provider-group regression with 1 January inspection; no false publication claim | PASS |
| Frozen fixture/output consistency | 30 fixture assertions; JSON/CSV provenance equality; all IDs, accepted dates and supplied hashes in PDF text | PASS |
| Scope/edition consistency | 8 isolated Postgres tests include materialised contract and actual TypeScript SQL/Brief parity; version bumped to 2 | PASS |
| Required independent acceptance | Grok journey retest then different-model approved-provider challenge | QUEUED, NOT RUN |

128 backend, 8 isolated Postgres and 9 frontend tests passed; TypeScript and candidate whitespace checks passed. Representative regenerated PDF page 15 visually checked; text checks cover all fixtures. Earlier PDF representative layout checks are retained in the prior packet. Supplementary reviewer found a legacy narrative date-substitution defect, corrected before final freeze. No release approval or full live/customer journey acceptance is implied. No current network/source revalidation, production import, paid transaction or delivery was performed. Checkout/delivery gates unchanged.
