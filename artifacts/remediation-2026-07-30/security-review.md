# Security review

Scope: keys, authentication, browser storage, remote media, personal-data intake,
exports, webhooks, email rendering, dependencies and deletion/retention workflows.

## Threat model summary

| Threat | Control | Residual risk |
|---|---|---|
| Secret disclosure | Environment/secret-manager loading, tracked-file scan, `.projects/` ignored | Operational key rotation and access review still require named owner |
| Privilege spoofing | Server-side API-key/auth checks; claim email bound to verified account | Authentication assurance level needs Human Gate definition |
| Claim takeover | Current identity/authority evidence, expiry, fingerprint-only storage, separate moderator | External evidence-check procedure and trained approvers still required |
| SSRF/tracking through media | Remote provider media false by default; CSP image sources limited to self/data | Re-enable only with proxy allowlist, scanning and privacy review |
| XSS in notifications | User/source strings escaped before email HTML insertion | Continue template review when adding fields |
| Export/exfiltration | Export delivery and lead intake false by default; scoped expiring tokens | Token hashing at rest remains a recommended hardening item |
| Webhook SSRF/replay | Public-destination validation, signing, idempotent delivery log | DNS rebinding/egress control should be tested in deployment network |
| Personal-data over-retention | Account deletion minimisation and nightly delete/anonymise rules | Nightly scheduling and evidence of successful runs require operations owner |
| Dependency compromise | Next/React upgraded; production npm audit clean at review time | Continuous update monitoring required |

## Browser storage

The frontend stores non-secret user id/name/email and displayed tier in local
storage. It does not intentionally store password, API key or session secret.
Authorization remains server-side. Residual risk: shared-device disclosure of
name/email until logout or storage clearing. A future hardening change should use
minimal server-backed session state.

The frontend no longer searches parent directories for a root `.env`; server API
credentials must be supplied through explicitly scoped runtime environment variables.

## STRIDE/DREAD disposition

Highest pre-control risks were claim spoofing/elevation, export disclosure, SSRF
through remote URLs, and secret leakage. Default-off gates reduce exploitability,
but do not make unapproved features launchable. No production keys were printed or
changed. The scanner reported 39 tracked matches: test passwords, test token
secrets and lockfile hash strings; manual classification found no tracked live
credential pattern. It also reported six matches inside ignored local `.projects`
vault/cache paths. Their values were not displayed or modified; those paths are
now explicitly excluded from version control and still require normal local-vault
access controls and rotation discipline.

## Activation requirements

- Named security owner and deputy; access/MFA/rotation evidence.
- Deployment-specific processor, region, encryption, backup and restore review.
- Egress and webhook replay exercise.
- Retention job schedule plus auditable run results.
- Incident, breach and data-subject request runbooks exercised.
