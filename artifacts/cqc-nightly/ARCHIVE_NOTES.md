# Historical CQC evidence archive review — 2026-10-01

These reports are saved observations, not live checks performed on October 1 by
this reviewer. Original report bytes are preserved; this note qualifies their use.
No checkout, collection, delivery, lead, claim or export gate is approved here.

- September 21–23 reports incorrectly use a seven-day poll requirement of 336.
  The checkpoint and September 24 onward reports use 24 required, 28 scheduled.
  Do not use the earlier requirement to assess readiness.
- The September 23 report predates the successful afternoon reconciliation.
  September 24 records the September 23 13:18:04 UTC completed watermark.
- `snapshot_changed` compares the newest stored checksum, which may belong to a
  report index or location index. The Markdown assertion that CQC published a new
  source snapshot does not establish a directory CSV change. Treat it as a stored
  index checksum change only, pending comparison of matching source types.
- Source snapshot counts and the later active database count can differ in time
  and scope. A nonzero delta is an observation to investigate, not proof of error.
- Event counts include rating-status changes; they are not all substantive rating
  movements, registrations or closures. September 30 and October 1 rolling 24-hour
  windows overlap because their execution times differ; do not add them as disjoint days.
- The repair-watch log is historical failure evidence, not proof of repair success.
  Its environment credential values were already masked. An unrelated provider-search
  response was removed and trailing whitespace normalized for public archiving. Other content consists of workflow
  diagnostics, public CQC source URLs, IDs, checksums and aggregate health/count data.
- `state.json` is a mutable local comparison cache and is deliberately ignored.

## Provenance

SHA-256 hashes identify the archived bytes. They establish file identity, not
independent verification of the observations. Original uncommitted files were saved
locally in `.tmp/commit-review-originals-2026-10-01.tar.gz` before editing.

Original repair-watch log SHA-256: `eb8c0a1df8ea014f905ea40b0a2cfde275ddd7c63e0d6998981606057fa91c26`

- `2026-09-20-503-repair-watch.log`: `879dabaa1003b6d5990401dfcc1d18cdab3a1cb71f5825ef9eb6dc87a46c5085`
- `2026-09-21-report.json`: `298892e60126fd6403ed95c821fe9304549bc605a4c333af7670d21ae3e26aef`
- `2026-09-21-report.md`: `3e51355e0fd8dde6384c92add40369ffd3ea7055042ebcfb658a09dbe53d56e7`
- `2026-09-22-report.json`: `18b4cc506ad61aa937b107da0d39f55df1cc537b88673862b9a7a0da1edf279f`
- `2026-09-22-report.md`: `b07dc8ec7416df2ee0647ab7cca623487ab39ad920cfeb26d6b5c6bf162b5e14`
- `2026-09-23-report.json`: `29da16f51bc4ae13893f0ed1da9305c5863f6d55121dfe6b8f97bae467012a24`
- `2026-09-23-report.md`: `a3eb2aaa27edd9d60cda43e83308403284e058e2cb4c7e84a4ba162526fa74a8`
- `2026-09-24-report.json`: `096150b691e12aca5ce8e31d5a53d0fc3ffb035d3ce58e409de6be70ba0b0a0c`
- `2026-09-24-report.md`: `7daccdb3ba044d5cae48156908156fa502b78ec29cd1381f8552abcab0b42dd9`
- `2026-09-25-report.json`: `e97af0d8224aace64920fe83e8b14ef32147aa99d3b4d02489a021ad1688dd27`
- `2026-09-25-report.md`: `f0eef4b764f47df5ebb14b97689f6fb61304964096ad89594b1ec839b6b27847`
- `2026-09-26-report.json`: `22fb8d029f8cb027d562aa064895d6317045c4fa2298c3388800e75c7b3c3e71`
- `2026-09-26-report.md`: `701d2baf4bbe5e335b48e0379582f7c1cd55ce9c359cd7d98de1a911ab131259`
- `2026-09-27-report.json`: `9a2340093b2d829e9c0431dcdbc57fb0b98b9488ce05fb7273d11f2050968818`
- `2026-09-27-report.md`: `d3876ab485e3a8d05db768f09d08857345df2eea35eab71ee6c0245462315e25`
- `2026-09-28-report.json`: `6f400c8850fa9b48de360aa29d2c5d7931fea725af8d7ceaf9372eb39e1dfdc4`
- `2026-09-28-report.md`: `1ed4197e713d94cf6450237e148c7662abd79bb4ee489f6e2999e76882464ad8`
- `2026-09-29-report.json`: `6a98ef642ffced9431785e363dcc206b24534e3336eb493c188e48bd2096faa7`
- `2026-09-29-report.md`: `c6529b9104d59440e2dc31e296077542ff8c2033ee66c2872f965d8c47064319`
- `2026-09-30-report.json`: `93f7eb0dc4eabe61fdc6925bea5b68d23a6b1b9fb00fc5e021e8265a626e1fe1`
- `2026-09-30-report.md`: `3c44adb06ef94e8d036b5f27e4d8c8929c5447be14a489caab4d273017728d70`
- `2026-10-01-report.json`: `de66b076ff55ef92996846596f0672140d8715104d2cd8553967d48dfe8c6c02`
- `2026-10-01-report.md`: `2c2f54a6102eefd6617a03ed67fafab8ee21b5a01f82132d80c858da486d6a23`
