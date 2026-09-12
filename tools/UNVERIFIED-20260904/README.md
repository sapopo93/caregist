# UNVERIFIED — quarantined 2026-09-04

Seven tools written by an AI agent in one session on 2026-09-04. **None has passed
independent QA.** They are kept for the record and for whatever is salvageable; they
are not on a trusted path and must not be scheduled, imported, or run against
production without a rewrite and a review by a different model, per
`ai-company-independent-qa`.

They were quarantined rather than repaired because a tool that misreports its own
status is more dangerous than no tool.

## Why — the defect that matters most

`run_cqc_reconciliation.py` and `self_heal.py --heal` both invoke
`incremental_update.py --phase finalize` **without `--snapshot-manifest`**, which
`_finalize_batch` (`incremental_update.py:1302`) requires. That raises `ValueError`.

The raise is caught by the generic handler at `incremental_update.py:1526-1546`, which
— whenever `--batch-id` is set and `--dry-run` is not — executes:

```
UPDATE reconciliation_batches SET status = 'failed' ...
UPDATE pipeline_runs SET status = 'failed', counts_reconciled = FALSE, reconciled_at = NULL ...
```

So a failed finalize does not merely fail. **It writes off a healthy, fully-sharded
batch as failed and destroys its watermark** — precisely the August end-state these
tools were written to prevent. `self_heal.py --heal` ran twice against production on
2026-09-04 and caused no damage only because no in-SLA stranded batch existed at those
moments.

## Other defects found (red-team pass, unrepaired)

Ranked; verified ones marked. Several were reported by the reviewer and **disproved**
on check — recorded here so nobody re-acts on them.

| file | line | defect | status |
|---|---|---|---|
| `run_cqc_reconciliation.py` | 164 | finalize without `--snapshot-manifest` | **verified** |
| `self_heal.py` | 143-145 | same defect in `--heal` | **verified** |
| `run_cqc_reconciliation.py` | 167-169 | on that failure prints "the batch is still open — do NOT abort it", which is false at the moment it prints | **verified** |
| `run_cqc_reconciliation.py` | 109-111 | `--dry-run` is never forwarded to the CLI, which has a real one. A "dry run" opens a real batch, calls the CQC API and upserts ~57k production rows | **verified by code read** |
| `run_cqc_reconciliation.py` | 95 vs 104 | resume looks for the manifest in `outreach/recon/`; prepare defaults to `tempfile.mkdtemp()`, so a batch this tool prepares can never be resumed by it | **verified by code read** |
| `build_inspection_target_list.py` | 251 | `_ = company_id` unbound if every row hits `continue` — NameError on re-run instead of "0 inserted" | **verified by code read** |
| `self_heal.py` | 165 | counts permanently-failed / future-dated `pending_emails` as backlog, pinning the check on forever | **verified by code read** |
| `incremental_update.py` | 676 | only `phone` is clamped; `postcode`, `town`, `county`, `region`, `local_authority`, `name`, `address_line1` take unclamped CQC free text. Migration 059's own principle applied to 1 of ~15 columns | **verified by code read** |
| `import_screening_results.py` | 127 | no `FOR UPDATE`; the API path has it (`api/routers/crm_extended.py:355`). Read-then-write race can overwrite a `consent_override` | **verified by code read** |
| `import_screening_results.py` | 218 | writes no audit row; the API path writes `crm.phone_screening.import` | **verified by code read** |
| `build_inspection_target_list.py` | 215 | `crm_contacts.company_id` never set — every company row orphaned | **verified by code read** |
| ~~`import_screening_results.py`~~ | ~~184~~ | ~~`status='invalid'` violates CHECK constraints~~ | **DISPROVED** — `invalid` is permitted on both `crm_contacts.phone_screening_status` and `crm_phone_screening_events.status`; the reviewer read migration 053 and missed 055 widening it |
| ~~all DB tools~~ | — | ~~RLS blocks them; export silently returns 0 rows~~ | **DISPROVED** — RLS is FORCE-enabled but `crm_contacts` returns 297 rows to `neondb_owner`; the export empirically returned 249. *Why* a FORCE-RLS table is readable by this role is unexamined and may itself be worth a look — but it is not these tools' bug |

## What was actually sound

- The CTPS economics finding: the cheap path is a licensed **bulk file** via
  `crm_phone_screening_imports` (`api/routers/crm_extended.py:297`), not the paid
  per-lookup TPSCheck API. `crm_phone_screening_cache` is UNIQUE on
  `(organization_id, phone_hmac)`, so a number is never paid for twice.
- `import_screening_results.py`'s write path was exercised end-to-end in a throwaway
  org and wrote all five tables correctly. That test was real. It does not make the
  tool fit for production, given the defects above.
- Migration `059`'s diagnosis: CQC published location `1-29250185054` with
  `mainPhoneNumber = '0794989994707949899947'` (22 chars, the number typed twice),
  which overflowed `varchar(20)` and killed shard 1 of batch `7fac8994` at offset 4787.
  Confirmed by rebuilding the shard partition from the same CSV via
  `crc32(location_id) % 8` — 7,171 ids, matching the recorded `expected_count` — and
  fetching that record from the CQC API. On the 2026-09-04 rerun, shard 1 passed
  `processed_count` 5250, beyond that offset.

## Not salvage without a Go

These serve a **parked** outcome. The active outcome is the CareGist founding-buyer
pilot (£150, consultancies, email). Nothing here moves
CONTACTED / REPLIED / ASKED_TO_PAY / PAID.
