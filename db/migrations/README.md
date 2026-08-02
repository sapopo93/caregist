# Migration governance

CareGist production migrations are forward-only. Once a migration filename is recorded in `schema_migrations`, do not edit, rename, reorder, or delete it. Correct released defects with a new uniquely numbered migration.

## Numbering

- Use the next unused three-digit number.
- A number may identify exactly one new migration.
- `034_named_care_groups_view.sql` and `034_verification_token_expiry.sql` are a frozen historical exception because both were already applied before the collision was found.
- Never rename either `034` file. Migration governance allowlists only that exact pair and rejects every other duplicate number.
- Numbers `043` and later remain unique even though `034` is reserved historically.

Run the mechanical gate before review:

```bash
python3 tools/check_migration_governance.py
```

## Production recovery policy

Use additive expand/contract changes wherever possible. For an isolated defect, deploy a new forward-fix migration. Do not run a down migration against production as an ordinary rollback mechanism. Files under `db/migrations/down/` document reversibility and support controlled non-production verification; they do not override this policy.

For destructive or irrecoverable corruption only, disable affected capabilities, restore through Neon point-in-time recovery, and rerun the full schema, smoke, and reconciliation checks. A verified Neon recovery point is mandatory before every production migration.

See `workflows/apply-migrations.md` and `workflows/neon-pitr-restore-drill.md`.
