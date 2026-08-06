# Neon PITR and restore drill

## Status and hard gate

Neon point-in-time recovery is CareGist's sole database recovery strategy. Production release is blocked until the deployment owner has evidenced a **minimum seven-day restore window** on the production project. If the current plan cannot provide seven days, upgrade it before migrations or commercial enablement. Repository text and provider credentials are not evidence that the window is configured.

Authoritative provider model: [Neon branch restore](https://neon.com/docs/introduction/branch-restore).

Targets:

- RPO: within the evidenced Neon history window.
- RTO: less than 30 minutes from approved drill start to invariant completion.
- Frequency: monthly and before any destructive/high-risk migration.

## Safety rules

- Never expose connection strings, API keys, row-level personal data, or screenshots containing them in evidence.
- Restore to a new isolated branch. Never overwrite the production branch during a drill.
- Use read-only invariant checks against the temporary branch.
- Do not delete the restored branch until the named approver has accepted the evidence.
- A failed or incomplete drill leaves the release gate red; do not infer success from branch creation alone.

## Pre-migration recovery point

1. Confirm the production project and branch identifiers without copying credentials into the ticket.
2. Verify the seven-day history window in Neon and record the provider evidence reference.
3. Record UTC time, deployed Git SHA, latest migration filename, authoritative reconciliation batch/watermark, and active location count.
4. Create a timestamped recovery branch at the pre-migration point, for example `recovery/pre-migration-YYYYMMDDTHHMMSSZ`.
5. Record the Neon project/branch IDs and creation operation ID in the controlled evidence system.
6. Only then run `db/apply_migrations.py --target production --confirm-production-backup`.

## Monthly isolated restore drill

1. Open `ops/evidence/restore-drill-template.md`; assign operator and approver.
2. Choose a target timestamp inside the seven-day history window and record why it is representative.
3. Create a temporary branch from that timestamp using Neon Console/API/CLI. Do not attach it to production traffic.
4. Obtain a pooled connection string through the approved secret channel and expose it only as `RESTORE_DATABASE_URL` in the operator shell.
5. Run read-only invariants:

   ```bash
   .venv/bin/python tools/verify_restore_invariants.py \
     --database-url "$RESTORE_DATABASE_URL" \
     --required-migration 044_b2b_contract_acceptance.sql \
     --minimum-provider-rows <approved-baseline> \
     --minimum-active-provider-rows <approved-baseline>
   ```

6. Run application smoke tests against an isolated deployment bound to the restored branch. Commercial flags remain false.
7. Record the restore target, actual restored point, RPO, RTO, invariant JSON, smoke SHA, and discrepancies. Store only redacted output.
8. The approver marks pass/fail. A pass requires every invariant, schema replay compatibility, and smoke check to succeed within the RTO.
9. After approval, delete the temporary compute/branch through Neon and record the deletion operation ID. Never automate this approval boundary.

## Incident recovery

Disable affected capabilities first. Prefer application rollback while schema compatibility remains intact, then a forward-fix migration for isolated defects. Use PITR only when the data/schema damage is destructive or cannot be corrected safely. After PITR, treat the restored branch as a new production candidate: validate migrations, counts, tenant/auth boundaries, exact release SHA, Stripe/webhook replay safety, source watermark, and a complete reconciliation before restoring traffic.
