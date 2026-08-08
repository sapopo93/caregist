# Migration Rollback Runbook

> **Mortar / Phase B — Caregist** | Generated 2026-05-16

This runbook documents the rollback procedure for migrations 020–029.
For irreversible migrations, the only safe recovery path is the snapshot restore
described in `workflows/restore-from-snapshot.md` (Bedrock PR #3).

---

## Migration reversibility table

| # | Migration | Reversible? | Downgrade script |
|---|-----------|-------------|------------------|
| 020 | pipeline_runs | YES | `db/migrations/downgrades/020_pipeline_runs_downgrade.sql` |
| 021 | password_reset_tokens | YES | `db/migrations/downgrades/021_password_reset_tokens_downgrade.sql` |
| 022 | admin_audit_log | YES | `db/migrations/downgrades/022_admin_audit_log_downgrade.sql` |
| 023 | claims_idempotency | PARTIAL — schema reversible; rejected-row mutation is not | `db/migrations/downgrades/023_claims_idempotency_downgrade.sql` |
| 024 | profile_completeness_function | YES (function drop only) | `db/migrations/downgrades/024_profile_completeness_function_downgrade.sql` |
| 025 | care_provider_slug_invariant | YES | `db/migrations/downgrades/025_care_provider_slug_invariant_downgrade.sql` |
| 026 | hash_api_keys | **NOT REVERSIBLE** | `db/migrations/downgrades/026_hash_api_keys_downgrade.sql` |
| 027 | user_sessions | YES | `db/migrations/downgrades/027_user_sessions_downgrade.sql` |
| 028 | audit_log | YES | `db/migrations/downgrades/028_audit_log_downgrade.sql` |
| 029 | password_reset_token_entropy | **NOT REVERSIBLE** | `db/migrations/downgrades/029_password_reset_token_entropy_downgrade.sql` |

---

## Step-by-step rollback procedure

### Before you start

- [ ] Confirm the target environment (production / staging)
- [ ] Take a database snapshot **now** even if one exists (Neon branch or RDS snapshot)
- [ ] Coordinate a maintenance window — most downgrades terminate live sessions or break active flows
- [ ] Check for application code that depends on the schema you are removing
- [ ] Have the snapshot restore playbook ready: `workflows/restore-from-snapshot.md`

### For reversible migrations

1. **Identify** which migration you are rolling back and open its downgrade script.
2. **Review** the risk notes at the top of the script.
3. **Run in a transaction** where possible:
   ```sql
   BEGIN;
   \i db/migrations/downgrades/<NNN>_<name>_downgrade.sql
   -- Inspect: does the database look correct?
   COMMIT;  -- or ROLLBACK if something looks wrong
   ```
4. **Remove the schema_migrations entry** so the migration will re-apply cleanly if needed:
   ```sql
   DELETE FROM schema_migrations WHERE filename = '<NNN>_<name>.sql';
   ```
5. **Deploy application code** that no longer relies on the removed schema object.
6. **Verify** the application is healthy before closing the window.

### For irreversible migrations (026, 029)

Do not attempt a SQL-level rollback. Follow the snapshot restore path:

1. Open `workflows/restore-from-snapshot.md` (Bedrock PR #3).
2. Restore to the snapshot taken immediately before the migration was applied.
3. Reconcile any data written after the snapshot was taken.

---

## Per-migration risk profiles

### 020 — pipeline_runs
- **Risk: LOW** (operational metadata only)
- Dropping the table deletes all pipeline run history used by health-check dashboards and alerts.
- Alerting systems that query `pipeline_runs` will error immediately after rollback.
- Safe to roll back if monitoring is temporarily suspended.

### 021 — password_reset_tokens
- **Risk: HIGH** (live user flows)
- Active password-reset requests will fail immediately; all in-flight tokens are invalidated.
- Users mid-reset will receive a broken experience.
- Roll back only during low-traffic window; notify support team.

### 022 — admin_audit_log
- **Risk: MEDIUM** (compliance)
- All recorded admin-moderation actions are destroyed.
- If audit trail is required for compliance, confirm with legal/compliance before proceeding.
- Application code writing to `admin_audit_log` will error post-rollback.

### 023 — claims_idempotency (PARTIAL)
- **Risk: MEDIUM**
- Schema objects (index, column) are dropped cleanly.
- Provider claims that were auto-rejected by this migration remain rejected; restoring them requires a pre-migration snapshot.
- The partial unique index on pending claims is removed, so duplicate pending claims are possible again until the migration is re-applied.

### 024 — profile_completeness_function
- **Risk: LOW-MEDIUM**
- The `calculate_profile_completeness` SQL function is dropped. Any application or SQL calling it will raise "function does not exist".
- The `profile_completeness` column on `care_providers` is NOT dropped; data is preserved.
- Application code must fall back to the inline CASE expression from migration 010 after rollback.

### 025 — care_provider_slug_invariant
- **Risk: LOW**
- Drops the CHECK constraint. Empty/sentinel slugs can be inserted again.
- Run the slug backfill again before re-applying this migration.

### 026 — hash_api_keys (NOT REVERSIBLE)
- **Risk: CRITICAL**
- Plaintext API keys were hashed with SHA-256 (one-way) and the originals NULLed. They cannot be recovered.
- All API key authentication will break if schema objects are dropped without a snapshot restore.
- Cross-reference: Forge PR #5 (`030_encrypt_webhook_signing_secrets`) uses the same backfill pattern.
- **Action required: restore from snapshot. See `workflows/restore-from-snapshot.md`.**

### 027 — user_sessions
- **Risk: HIGH** (all active sessions terminated)
- Every authenticated user session is destroyed when the table is dropped.
- All logged-in users are immediately signed out.
- Roll back only during low-traffic window.
- **Order dependency**: roll back before migration 026 if FKs are enforced (api_key_id column).

### 028 — audit_log
- **Risk: MEDIUM-HIGH** (security compliance)
- Destroys all security audit history (auth, billing, admin, internal events).
- If security audit logs are required for compliance, confirm with security team before proceeding.

### 029 — password_reset_token_entropy (NOT REVERSIBLE)
- **Risk: HIGH**
- The token column was changed from VARCHAR(10) to TEXT. Reverting would truncate long tokens.
- All in-flight high-entropy tokens would be silently corrupted.
- **Action required: restore from snapshot. See `workflows/restore-from-snapshot.md`.**

---

## Coordination notes

- **Forge PR #5** — `030_encrypt_webhook_signing_secrets` is in the same irreversible backfill class as 026. If 026 is being restored from snapshot, verify whether 030 has also been applied and whether the snapshot predates it.
- **Spool PR #9** — `031_session_table.sql` creates an additional session table; downgrade is reversible (drop table). Not covered in this runbook (migrations >029 are out of scope for Phase B).
- **Bedrock PR #3** — `workflows/restore-from-snapshot.md` is the canonical restore procedure referenced throughout this runbook.
