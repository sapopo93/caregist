# Territory Brief Postgres source

Runtime generation now reads original CQC evidence from immutable Postgres
editions. Neither checkout nor fulfilment reads repository NDJSON files.
The file-based CLI generator remains available for offline work.

## Load an edition

Apply migration `066_territory_brief_source_editions.sql` through the normal
approved migration process. On the collection host, import a complete,
reconciled pair of original CQC location/provider exports:

```sh
.venv/bin/python -m tools.import_territory_brief_source \
  --locations-source /path/to/locations.ndjson \
  --providers-source /path/to/providers.ndjson \
  --source-retrieved-at '<ISO-8601 timestamp from the collection receipt>'
```

The importer reads `DATABASE_URL` from the environment. Preserve the collection
receipt: the supplied retrieval timestamp is operator evidence, not independent
proof of reconciliation. Do not substitute import time or file modification time.
The importer does not collect missing exports or manufacture rating history from
current directory rows. A verified source export must still be supplied before
this can operate in production.

The import streams records in batches inside one transaction. Duplicate location
IDs, missing provider identity/name, empty/undated inputs, future source dates,
and files changed during import abort the transaction. Original CQC location payloads,
including historic/current rating blocks, remain intact. Full source-file hashes
and the newest source event date identify the edition. Re-importing identical
files is rejected by the unique hash pair; existing editions cannot be restamped.

## Checkout and recovery

Checkout selects the latest imported edition, rejects a retrieval age over the
existing eight-day source SLA, verifies its stored row count, and generates the
requested shortlist before creating a Stripe session. An insufficient shortlist
or a territory exceeding 25,000 source locations returns unavailable before
payment. The selected edition ID is saved with the reserved order.

Fulfilment loads that pinned edition using its existing webhook database
connection. A later edition or the loss of files on the collection/runtime host
does not change the order's evidence. Paid retries may use an aged pinned edition;
they cannot switch silently to a newer edition. Database unavailability still
fails and follows the existing failure/retry path.

Source rows are sealed when their import transaction commits. Updates, deletes,
truncation and subsequent inserts are rejected. Orders reference their edition
with deletion restricted. This does not replace database backups or protect
against an administrator deliberately disabling database controls.

Existing orders without a source edition fail explicitly and require evidence-
reviewed recovery. Do not automatically assign today's edition to an old payment.

## Verification and remaining release gates

| Promise | Evidence / pass condition |
| --- | --- |
| Runtime does not need local exports | Real-Postgres tests delete imported files, then generate PDF/CSV and complete paid fulfilment. |
| Rating history and provider attribution survive | Synthetic source has a dated RI-to-Good transition; generated CSV retains the transition and verified organisation name. Mixed-case territory names and whitespace provider IDs are covered. |
| Retries retain original evidence | Import a newer edition with different names; the original order still produces its original CSV. |
| Bad source cannot start checkout | Empty, stale, incomplete and undersized edition tests; checkout source-error test asserts Stripe session creation never occurs. |
| Evidence cannot be cleaned up under a paid order | Real-Postgres tests reject deletion, truncation and inserts into committed editions. |
| Customer artifacts remain readable | Synthetic PDF first page and provenance page rendered and visually inspected; extracted text reconciled to 12 source providers, 10 shortlisted providers and dated rating changes. |

These are local synthetic checks. No production source import, live payment,
Blob upload, outbound delivery, deployment or commercial activation is proved by
them. National-scale time/memory limits, authoritative source reconciliation,
required independent model gates and existing legal/commercial gates remain
release requirements. Checkout flags remain closed.

Local verification on 18 October 2026: **158 passed**, with no skips, across
`test_territory_source_pg`, the existing Postgres fulfilment/download suites,
checkout, fulfilment, acceptance gates/email, generator and output-fix suites.
`tools/check_migration_governance.py` and `git diff --check` also passed.
The independent bounded static review found territory casing, provider-ID
normalization and edition mutation gaps; these were fixed and re-reviewed.
The final full paid-path test additionally caught and fixed the missing
`source_edition_id` in the fulfilment order SELECT. This is local repair evidence,
not a completed Grok/DeepSeek commercial gate.
