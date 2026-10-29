# Local Territory Brief rating contract candidate

Implemented locally only; no release approval. All 30 ratings are based on the frozen 22 October audit, not a fresh website check.

`fixtures.json` retains frozen API payloads, file evidence and qualified website observations. `rating-evidence.json` is an explicit supplemental input keyed by location ID; it is not an automatically loaded list of production overrides. No location-ID exceptions are embedded in the resolver. The two contextual cases are unresolved; Check House's API/website Outstanding evidence is explicitly inherited/contextual, while the newer file Good remains retained and unresolved.

The generator uses one versioned current-state contract for rating values, narrative, evidence dates, JSON, CSV and PDF. Rating scope consumes the same contract materialised in an immutable edition. Unsupported/missing contracts, malformed statuses, equal-date or undated conflicts fail closed. Scope excludes deregistered/dormant records and resolves service aliases through the existing shared taxonomy. Public rating coverage reports the edition ID and checks edition completeness and freshness.

Importer changes accept `--rating-evidence PATH` to pin supplemental evidence into a new edition, preserve source hashes, include supplemental bytes in edition identity, include newer publication dates in `source_as_of`, and reject dates beyond retrieval or unmatched IDs. No importer was run against production. Old editions without the contract are refused by the Brief loader; preparing a new evidence edition is a separate operational step, not authorised here.

The exact recovered file hash maps to **CQC download edition 2 October 2026; data cutoff unverified**. Individual rating publication dates are separate. This does not establish a 2 October data cutoff or relabel other unverified files.

`brief.pdf`, `brief.csv` and `brief.json` are synthetic acceptance artifacts produced through the actual generator/exporters: all locations are deliberately placed in Fixture County, given synthetic provider identities and a 20 October registration signal so all 30 can be inspected together. These artificial scope/registration/provider fields are not findings about the locations. Original fields remain in `fixtures.json`; the artifacts are not a customer-ready Brief or evidence of paid delivery. Rating evidence is unchanged by the synthetic wrapper.

Plan completed locally: define contract; connect edition input and outputs; validate fixtures and scope; freeze packet; queue required reviews. See `REVIEW_QUEUE.md`; required Grok/different-model reviews remain pending. Checkout, collectors, outbound delivery, leads, claims and exports retain their existing commercial gates.
