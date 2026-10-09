# Open PR inventory — 9 October 2026

Patch equivalence is narrower than semantic overlap. Unmatched patches do not prove a feature is missing. No PR was merged or closed during this audit.

| PR | Title | Behind main | Branch commits | Unmatched patches | Disposition |
|---|---|---:|---:|---:|---|
| [#83](https://github.com/sapopo93/caregist/pull/83) | Territory Brief output fixes, outbound email gate, and acceptance tests | 0 | 6 | 6 | Six commits integrated into this repair branch; not approved or merged. |
| [#81](https://github.com/sapopo93/caregist/pull/81) | Run Territory Brief fulfilment against real Postgres in CI | 12 | 2 | 2 | Existing mandatory PG journey overlaps; dependency change requires separate review. |
| [#72](https://github.com/sapopo93/caregist/pull/72) | Expose bounded reconciliation acknowledgement recovery | 55 | 2 | 2 | Recovery acknowledgement requires independent safety review; no bypass. |
| [#71](https://github.com/sapopo93/caregist/pull/71) | Freeze polling, territory intake, and release evidence gates | 33 | 6 | 6 | Older evidence gate branch; compare semantically before merge. |
| [#51](https://github.com/sapopo93/caregist/pull/51) | Prepare manual Territory Brief delivery proof and restore test-mode gate | 109 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#49](https://github.com/sapopo93/caregist/pull/49) | Territory Brief: fulfilment/download hardening + pre-payment Price validation (NOT release-ready) | 149 | 20 | 20 | Old fulfilment branch; do not replace current implementation. |
| [#48](https://github.com/sapopo93/caregist/pull/48) | fix(security): patch frontend image dependencies | 110 | 1 | 1 | Current frontend audit fixes already merged via PR82; inspect exact dependency delta. |
| [#45](https://github.com/sapopo93/caregist/pull/45) | fix(ci): install freshness watchdog runtime dependencies | 110 | 2 | 2 | Watchdog now runs; old dependency proposal is not evidence of current break. |
| [#40](https://github.com/sapopo93/caregist/pull/40) | feat(ai-os): add governed task, evidence and independent-review loop | 110 | 27 | 27 | Unreviewed old proposal; no automatic merge. |
| [#37](https://github.com/sapopo93/caregist/pull/37) | fix(release): integrate reviewed live-lineage remediations | 140 | 12 | 0 | All 12 patches equivalent to main; closure candidate. |
| [#26](https://github.com/sapopo93/caregist/pull/26) | Add gated CQC reconciliation pipeline | 249 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#23](https://github.com/sapopo93/caregist/pull/23) | legal: publish operative terms and privacy notice naming H-Kay Limited | 277 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#22](https://github.com/sapopo93/caregist/pull/22) | ci: CQC change detection workflow (schedule gated on two blockers) | 277 | 6 | 6 | Unreviewed old proposal; no automatic merge. |
| [#20](https://github.com/sapopo93/caregist/pull/20) | feat: account deletion (soft-delete + DSAR export) — Quill Phase B | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#19](https://github.com/sapopo93/caregist/pull/19) | docs: full README + runbook bundle (Phase B) | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#18](https://github.com/sapopo93/caregist/pull/18) | feat(ops): systemd timers replace cron, Prometheus /metrics endpoint | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#17](https://github.com/sapopo93/caregist/pull/17) | feat(claims): two-gate claim verification (CQC domain match + admin review) | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#16](https://github.com/sapopo93/caregist/pull/16) | feat(privacy): unbundled marketing consent + marketing_consent_at (GDPR Art 7) | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#15](https://github.com/sapopo93/caregist/pull/15) | test: webhook integration tests + subscriber HMAC verification + admin audit-log assertions | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#14](https://github.com/sapopo93/caregist/pull/14) | feat(db): migration downgrade scripts for migrations 020-029 + rollback runbook | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#13](https://github.com/sapopo93/caregist/pull/13) | security: bcrypt-only API key validation, migration 032 | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#12](https://github.com/sapopo93/caregist/pull/12) | chore(billing): audit Stripe price vars; remove orphaned ENTERPRISE var | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#11](https://github.com/sapopo93/caregist/pull/11) | feat(health): verify Stripe + Resend + Sentry availability in readiness endpoint | 285 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#10](https://github.com/sapopo93/caregist/pull/10) | feat(legal): UK GDPR privacy policy, DPIA template, ICO registration runbook, retention policy | 287 | 2 | 2 | Unreviewed old proposal; no automatic merge. |
| [#9](https://github.com/sapopo93/caregist/pull/9) | security: opaque session IDs, retire bearer-in-cookie (F#1) | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#8](https://github.com/sapopo93/caregist/pull/8) | feat(privacy): in-house cookie banner, strict CSP, third-party script gating | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#7](https://github.com/sapopo93/caregist/pull/7) | security(F#2): remove localStorage tokens, add Next.js middleware + HttpOnly cookie flow | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#6](https://github.com/sapopo93/caregist/pull/6) | security(F#4): remove NEXT_PUBLIC_API_KEY — route all backend calls through server-side proxy | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#5](https://github.com/sapopo93/caregist/pull/5) | feat(security): require WEBHOOK_SECRET_KEY, AES-GCM encrypt webhook signing secrets [F#3] | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#4](https://github.com/sapopo93/caregist/pull/4) | chore(security): harden .gitignore, pre-commit secret scanner, CI scan | 287 | 5 | 5 | Unreviewed old proposal; no automatic merge. |
| [#3](https://github.com/sapopo93/caregist/pull/3) | feat(infra): Terraform module, KMS CMK, daily S3 backups, restore runbook | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#2](https://github.com/sapopo93/caregist/pull/2) | chore: drop Redis, pin uvicorn to one worker | 287 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
| [#1](https://github.com/sapopo93/caregist/pull/1) | docs: Stripe key rotation runbook | 288 | 1 | 1 | Unreviewed old proposal; no automatic merge. |
