# Restore drill — procedure and evidence

Closes the "no restore runbook, no restore drill" half of `PRODUCTION_AUDIT.md` **F-7**.
It does **not** close the "no automated backup" half — see *Known limits* below.

## Why branch restore rather than dump/restore

Neon point-in-time branching restores a full copy of the database as it existed at a
chosen timestamp, **without copying personal data out of Neon**. A `pg_dump` drill would
place live user emails, password hashes and consumer lead data on an operator laptop,
creating a new copy to secure and delete. Branching avoids that entirely, and it is also
the mechanism you would genuinely use in an incident.

## Procedure

Requires `neonctl` authenticated against org `org-muddy-brook-84822640`.

Project IDs: CareGist `purple-voice-97710924` · LeadGen SA `ancient-pine-14685767`

1. Create a branch at the target timestamp (RFC3339, UTC, inside the retention window):

```bash
npx neonctl branches create --project-id purple-voice-97710924 --name restore-drill --parent 2026-08-01T20:56:03Z --output json
```

2. Connect using the returned `connection_uris[0].connection_uri` and verify row counts
   against the expected production baseline.
3. If this were a real incident, repoint the application at the branch, or promote it.
4. Delete the drill branch and confirm removal:

```bash
npx neonctl branches delete <branch-id> --project-id purple-voice-97710924
```

## Evidence — 1 August 2026

Both live projects restored to a timestamp one hour prior, verified, and torn down.

**CareGist** (`purple-voice-97710924`, branch `br-dawn-boat-abm8khku`) — restored copy matched
production exactly:

| Table | Rows |
|---|---|
| `care_providers` | 56,743 (all with a rating) |
| `provider_rating_history` | 43,041 |
| `trusted_event_ledger` | 56,746 |
| `users` | 5 |
| `subscriptions` | 3 |
| `pending_emails` | 31 |
| `schema_migrations` | 43 (latest applied 2026-07-31) |

**LeadGen SA** (`ancient-pine-14685767`, branch `br-round-silence-ab7tyqs1`) — restored and
verified; `leads` 14 rows, `audit_entries` 24 rows.

Both drill branches deleted; `branches list` confirms zero remaining.

**Verdict: restore works.** Recovery within the retention window is proven, not assumed.

## Known limits — these are the real risk

1. **The recovery window is 6 hours.** `history_retention_seconds` is 21,600 on both
   projects. This is the Neon **Free plan** ceiling — an API call setting 86,400 is
   accepted and silently clamped back to 6h. Corruption or deletion discovered more than
   six hours later is **unrecoverable**, because there is no second copy anywhere.
2. **There is still no automated backup.** Branch restore depends entirely on Neon's
   retained history. It is not a backup: it does not survive account loss, billing
   suspension, or a provider-side incident.
3. **No restore has been performed under incident conditions** — this drill was planned,
   unhurried, and run against a healthy database.

### Recommended fix, in order

1. Upgrade both projects to a Neon paid plan to raise retention to 7+ days. This is the
   single highest-value spend available and requires a purchase decision.
2. Add a scheduled logical dump to encrypted object storage for a copy that survives
   provider loss. CareGist already depends on `boto3`; no new vendor is required.
3. Repeat this drill quarterly and append evidence here, with the date and the operator.
