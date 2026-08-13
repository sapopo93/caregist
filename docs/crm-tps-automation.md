# CareGist CQC → TPSCheck → CRM automation

## Outcome

The worker converts filtered new-registration feed rows into CRM contacts without CSV exports or operator action.

1. The minute cron snapshots the enabled organisation's CareGist feed filters.
2. New CQC provider locations enter a durable, tenant-isolated queue.
3. UK national phone numbers are normalised to E.164.
4. CareGist checks TPSCheck credits, then starts at most 50 single-number v2 checks per run.
5. Each paid provider result is saved before CRM materialisation.
6. Clear numbers become assigned, callable CRM contacts.
7. TPS, CTPS and invalid numbers remain CRM contacts with a call-only suppression.
8. Provider email is retained, but email marketing remains disabled until an owner records a valid basis.

Operators cannot view credentials, credits, leases, retries or automation controls. They see only the normal CRM queue and the authoritative call status.

## Safety invariants

- The global environment flag and tenant setting must both be enabled.
- Unknown, malformed, failed or stale results never become callable.
- Screening results expire from the calling gate after 28 days; the worker requeues them on day 27.
- A TPS/CTPS/invalid result creates only a `channel = 'call'` suppression. It does not erase the organisation or its email.
- TPSCheck responses are schema-validated, hashed and audited.
- Every external request is counted before it starts; timeouts remain pessimistically charged to the CareGist cap.
- A saved provider response is reused after a CRM/database retry, avoiding a second paid check.
- Jobs use expiring leases, `SKIP LOCKED` and a global advisory lock to prevent duplicate cron work.
- The provider origin is fixed to `https://api.tpscheck.uk`; redirects and arbitrary hosts are rejected.
- The API key is server-only and never returned by an endpoint.

## Environment

```text
CRM_ENABLED=true
CRM_SCREENING_HASH_KEY=<at least 32 random characters>
CRM_TPS_AUTOMATION_ENABLED=true
CRM_TPSCHECK_API_KEY=<TPSCheck API key>
CRM_TPSCHECK_BASE_URL=https://api.tpscheck.uk
CRON_SECRET=<Vercel cron bearer secret>
```

Keep `CRM_TPS_AUTOMATION_ENABLED=false` until migration 055 is applied and TPSCheck reports sufficient credits.

## Owner configuration

An authenticated owner/admin configures the assigned CRM operator and the same filter fields used by the CareGist new-registration feed:

```http
PUT /api/v1/crm/tps-automation
Content-Type: application/json

{
  "enabled": true,
  "assigned_user_id": 123,
  "registered_from": "2026-08-01",
  "filters": {
    "region": "London",
    "service_type": "Homecare Agencies"
  },
  "max_monthly_checks": 10000,
  "per_run_limit": 50
}
```

Supported filters are `q`, `region`, `local_authority`, `service_type`, `provider_type`, `postcode_prefix`, `from_date` and `to_date`. `registered_from` is always the minimum boundary even if an earlier `from_date` is supplied.

Status is owner/admin-only:

```http
GET /api/v1/crm/tps-automation
```

## Capacity

The worker deliberately stays at 50 starts per minute, below the requested 60-per-minute allowance. A full 10,000-credit allowance takes about 200 minutes (3 hours 20 minutes), plus retries. The live `/credits` response remains authoritative for plan name, allowance and remaining credits.

## Monitoring

- `caregist_crm_tps_stale_organizations`
- `caregist_crm_tps_failed_organizations`
- `caregist_crm_tps_pending_jobs`
- `caregist_crm_tps_review_jobs`

Readiness fails if an enabled tenant has not run within three minutes or its latest run has an error. Review jobs are a warning backlog and do not expose details to operators.

## Rollback

1. Set the tenant's `enabled` value to `false`, or set `CRM_TPS_AUTOMATION_ENABLED=false` globally.
2. Confirm the cron reports `reason=disabled` and no jobs are processing.
3. Preserve completed screening events and audit evidence unless a separately approved retention action applies.
4. Use `db/migrations/down/055_crm_tps_automation.down.sql` only when intentionally removing the feature and its queue/settings data.

Calling is a separate activation gate. This worker can prepare the compliant queue while Twilio calling remains disabled.
