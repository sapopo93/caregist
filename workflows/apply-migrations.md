# Apply CareGist database migrations

`db/apply_migrations.py` applies each numbered SQL file in its own transaction and records its filename in `schema_migrations`. The production policy is forward-only and Neon PITR is the sole recovery mechanism.

## Invariants

- `db/init.sql` has been applied to a new database before numbered migrations.
- Staging and production use separate Neon projects/resources and distinct credentials.
- Staging receives the exact migration chain before production.
- Production has an evidenced seven-day Neon history window and a timestamped pre-migration recovery branch.
- The release Git SHA, current watermark/batch, counts, operator, approver, and recovery branch ID are recorded before migration.
- The exact historical `034` pair remains unchanged; every future number is unique.

Run the repository gates first:

```bash
python3 tools/check_migration_governance.py
pytest tests/integration/test_migrations_apply_cleanly.py -v
```

## Staging

Expose `STAGING_DATABASE_URL` through the approved secret channel, then run:

```bash
.venv/bin/python db/apply_migrations.py --target staging
```

Run schema, billing/webhook replay, reconciliation, and application smoke tests on staging. A passing migration command alone is not release evidence.

## Production

Follow `workflows/neon-pitr-restore-drill.md` to verify the history window and create the pre-migration recovery branch. Then expose `PROD_DATABASE_URL` through the approved secret channel and run:

```bash
.venv/bin/python db/apply_migrations.py \
  --target production \
  --confirm-production-backup
```

The confirmation flag records operator intent; it does not create or verify a recovery point. Do not use it until the provider evidence exists.

After migration:

1. Verify `schema_migrations` contains every expected filename.
2. Deploy the exact CI-tested SHA with all commercial/governed flags false.
3. Compare `/api/v1/version` and `/api/health/directory` with that SHA.
4. Run production smoke, `/data-status`, provider sitemap, auth/tenant, webhook replay, and database invariants.
5. Run the manual reconciliation and verify its checksum, coverage, counts, and watermark before enabling its schedule.

## Failure and rollback

If a migration file fails, its transaction is rolled back and its filename is not recorded. Stop; do not skip ahead. Fix an unreleased file before retrying, or add a new corrective migration if the faulty file has been released anywhere.

For an application defect, disable feature flags first and roll back code only while schema compatibility remains intact. For an isolated schema/data defect, use a new forward-fix migration. Use Neon PITR only for destructive or irrecoverable damage, then perform the complete restored-branch validation and reconciliation before sending traffic.

Never delete a production `schema_migrations` row to force replay, run a down migration as an ordinary production rollback, or restore over the production branch during a drill.
