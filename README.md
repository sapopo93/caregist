# Caregist

## Deployment runbook

All ship procedures for the May 2026 launch are consolidated in:

**[workflows/SHIP_RUNBOOK.md](workflows/SHIP_RUNBOOK.md)**

That document covers:
- Pre-flight access checks and key generation
- 4-wave merge order for all 20 PRs
- Per-migration count-check SQL and apply commands
- Env var table (what to generate vs what to copy from infra)
- Merge conflict resolution guide
- Post-deploy smoke tests (`bash scripts/post-deploy-smoke.sh`)
- June 1 follow-up procedure for payment-gated items (AWS/Bedrock, ICO reg, blue-green)

---

*Full README content is added by PR #19 (Quire). This stub links to the ship runbook and will be superseded by Quire's full rewrite. Take Quire's version on merge conflict.*
