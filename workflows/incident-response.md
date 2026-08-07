# Runbook: Incident Response

**Applies to:** All production incidents affecting `caregist.co.uk` and its backend API.

---

## Severity Levels

| Level | Name | Definition | Example | Initial response target |
|---|---|---|---|---|
| **P0** | Full outage | The site or API is completely unavailable, or data integrity is actively corrupted | Health check returning 5xx; database unreachable; all webhooks failing | Acknowledge within 15 min; all hands |
| **P1** | Significant degradation | A major feature is broken or severely slow; a subset of users cannot complete key workflows | Feed ingestion stalled >2 hours; email delivery failing; webhook delivery rate <50% | Acknowledge within 30 min; on-call engineer |
| **P2** | Minor / cosmetic | A non-critical feature is broken; workaround exists; no data loss | Minor UI rendering issue; a single webhook subscriber failing; slow search on one filter |  Acknowledge within 4 hours; normal business hours |

---

## On-Call Rotation

> **Placeholder — update before going live.**
>
> | Week | Engineer | Contact |
> |---|---|---|
> | Odd weeks | [Name] | [Slack / phone] |
> | Even weeks | [Name] | [Slack / phone] |
>
> Escalation path: on-call engineer → technical lead → owner.
> Primary alert channel: `#caregist-ops` in Slack (or equivalent).

---

## Incident Lifecycle

### 1. Detection

Incidents are typically detected via:
- Sentry alert (backend exception rate spike)
- Uptime monitor alert (health check `GET /api/v1/health` failing)
- User report via support
- Failed monitor-alerts tool run

### 2. Triage (P0/P1: within 15 min of alert)

```bash
# From the EC2 host — check service health
sudo systemctl status caregist-api
curl -s http://localhost:8000/api/v1/health

# Recent error logs
sudo journalctl -u caregist-api --since "30 minutes ago" | tail -100

# Database connectivity
psql "$DATABASE_URL" -c "SELECT 1;"

# Feed pipeline status
tail -50 /var/log/caregist/feed-cycle.log

# Email queue
tail -50 /var/log/caregist/email.log
```

### 3. Declare the incident

Once severity is confirmed:

1. Post in `#caregist-ops`: use the [communications template](#communications-template) below.
2. Open a tracking note (text file, Notion page, or GitHub issue) titled `YYYY-MM-DD-HH-incident-<slug>`. Record all actions taken with UTC timestamps.
3. For P0: notify any Business-tier customers with active webhook subscriptions within 30 minutes.

### 4. Mitigate

Apply the fastest available fix — even a partial mitigation (e.g., restart the service, roll back the last deploy). Record each action in the tracking note.

Relevant runbooks:
- Service restart: see [`deploy-ec2.md`](deploy-ec2.md)
- Database migration issue: see [`apply-migrations.md`](apply-migrations.md)
- Feed stalled: see [`run-feed-cycle.md`](run-feed-cycle.md) and [`cqc-fallback-activation.md`](cqc-fallback-activation.md)
- Email failures: see [`stuck-email-recovery.md`](stuck-email-recovery.md)
- Webhook failures: see [`webhook-debugging.md`](webhook-debugging.md)
- Secret compromise: see the relevant rotation runbook immediately

### 5. Resolve

Once the service is healthy and stable:

1. Confirm health check passes: `curl -s http://localhost:8000/api/v1/health`
2. Confirm Sentry error rate has returned to baseline.
3. Post resolution notice in `#caregist-ops` using the template.
4. Update any affected Business-tier customers.

### 6. Post-mortem (P0 and P1)

Post-mortem must be filed within **5 business days** of resolution. See the [post-mortem template](#post-mortem-template) below.

---

## Communications Template

### Incident declared

```
[INCIDENT DECLARED - P{LEVEL}]
Time (UTC): {YYYY-MM-DD HH:MM}
Incident: {one-line description}
Impact: {who is affected and how}
Status: Investigating
Next update: {time}
```

### Update during incident

```
[INCIDENT UPDATE - P{LEVEL}]
Time (UTC): {YYYY-MM-DD HH:MM}
Status: {Investigating / Identified / Mitigating}
Latest: {what was found or what action is in progress}
Next update: {time}
```

### Resolution

```
[INCIDENT RESOLVED - P{LEVEL}]
Time (UTC): {YYYY-MM-DD HH:MM}
Duration: {start to resolve, e.g. 47 minutes}
Root cause (preliminary): {one-line}
Post-mortem: {link or "to be filed by YYYY-MM-DD"}
```

---

## Incident Timeline Format

Record every significant action during the incident in chronological order:

```
YYYY-MM-DD HH:MM UTC  [ACTION/FINDING] Description of what happened or was discovered.
YYYY-MM-DD HH:MM UTC  [DEPLOY] Deployed commit abc1234 to fix X.
YYYY-MM-DD HH:MM UTC  [ROLLBACK] Rolled back to abc0000 — fix introduced new error.
YYYY-MM-DD HH:MM UTC  [RESOLVED] Health check passing; Sentry rate normal.
```

Keep the timeline append-only. Do not edit past entries.

---

## Post-Mortem Template

File post-mortems at `docs/incidents/YYYY-MM-DD-<slug>.md`.

```markdown
# Post-Mortem: {incident title}

**Date:** YYYY-MM-DD
**Severity:** P{0/1}
**Duration:** {start} – {end} UTC ({total minutes})
**Author:** {name}
**Reviewed by:** {name(s)}

## Summary

{2–3 sentence summary of what happened, its impact, and how it was resolved.}

## Timeline

{Paste the incident timeline here.}

## Root Cause

{Detailed technical explanation of what caused the incident.}

## Contributing Factors

- {Factor 1}
- {Factor 2}

## Impact

| Dimension | Detail |
|---|---|
| Users affected | {estimate} |
| Business-tier customers affected | {count / "none"} |
| Data integrity impact | {none / partial / full — describe} |
| Webhook delivery failures | {count / "none"} |
| Revenue impact | {estimate / "none identified"} |

## What Went Well

- {Thing that worked}

## What Could Be Improved

- {Improvement opportunity}

## Action Items

| Action | Owner | Due date |
|---|---|---|
| {action} | {name} | YYYY-MM-DD |

## Follow-up

Link to any related GitHub issues, PRs, or runbook updates that were created as a result of this incident.
```

---

## Standing Checks After Any P0 or P1

After resolving any P0 or P1, always verify:

1. `GET /api/v1/health` returns `{"status":"healthy"}` with HTTP 200.
2. Sentry error rate in the dashboard is at or below the pre-incident baseline.
3. Most recent CQC feed cycle completed without errors (check `pipeline_alert_log`).
4. At least one test email delivers successfully.
5. At least one Business-tier webhook delivers successfully (check audit log).
