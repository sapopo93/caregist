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

## Recovery window — fixed on 1 August 2026

Both projects were running `history_retention_seconds = 21600`, a **6-hour** recovery
window. Anything discovered more than six hours late was unrecoverable, because no second
copy exists anywhere.

This was **not** a plan limit. The owning organisation (`org-muddy-brook-84822640`) was
already on the paid **Launch** plan, which supports 7 days. The 6 hours was simply the
default carried from project creation — the capability was paid for and unused.

Raised to **7 days** (604,800s) on both projects at no additional cost:

```bash
curl -X PATCH "https://console.neon.tech/api/v2/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $NEON_TOKEN" -H "Content-Type: application/json" \
  -d '{"project":{"history_retention_seconds":604800}}'
```

Note `neonctl projects update` has **no** history-retention flag; it accepts and silently
ignores one, reporting success while changing nothing. Use the REST API and verify after.

## Remaining limits

1. **There is still no automated backup.** Branch restore depends entirely on Neon's
   retained history. It is not a backup: it does not survive account loss, billing
   suspension, or a provider-side incident.
2. **No restore has been performed under incident conditions** — this drill was planned,
   unhurried, and run against a healthy database.
3. **Both projects sit in `aws-eu-west-2` (London).** For LeadGen SA, a South African
   consumer-lead business, that is a POPIA cross-border transfer requiring a documented
   s.72 basis. Logical separation is not residency.

### Next, in order

1. Add a scheduled logical dump to encrypted object storage for a copy that survives
   provider loss. CareGist already depends on `boto3`; no new vendor is required.
2. Document the LeadGen SA transfer basis, or relocate that data plane.
3. Repeat this drill quarterly and append evidence here, with the date and the operator.
