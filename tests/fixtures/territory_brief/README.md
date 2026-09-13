# Territory Opportunity Brief - integration test fixture

`locations_detail.jsonl` / `providers_detail.jsonl` are a **field-trimmed extract
of the public CQC register** (the same shape as the operational
`_locations_detail.ndjson` / `_providers_detail.ndjson` snapshots) limited to
three South-coast local authorities: **Isle of Wight, Portsmouth, Southampton**
(1,422 locations, ~920 providers).

Only the keys the generator reads are kept
(`locationId`, `name`, `providerId`, `localAuthority`, `region`,
`registrationDate`, `registrationStatus`, `dormancy`, `numberOfBeds`,
`postalCode`, `gacServiceTypes`, `currentRatings`, `historicRatings`).

Source: CQC public register, edition mirrored February 2026.
Contains public sector information licensed under the Open Government Licence v3.0.

Used by `tests/test_territory_brief_integration.py`. The `.jsonl` extension keeps
it out of the repo-wide `*.ndjson` ignore rule while remaining line-delimited
JSON that `tools.generate_radar_territory_sample._load_ndjson` reads directly.

To regenerate against a fresh register, re-run the extract in the test-fixture
section of the Slice 2 delivery notes.
