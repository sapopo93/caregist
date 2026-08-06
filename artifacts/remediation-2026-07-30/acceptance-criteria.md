# Acceptance criteria

## Invariants

1. A completeness field is never described or sorted as provider care quality.
2. CQC snapshot reconciliation is all-or-nothing and records source URI,
   publication watermark, retrieval time, counts and outcome.
3. Every count carries its unit: location row, active location, CQC provider
   organisation or CareGist named group.
4. Invalid entity routes return 404 and empty sitemap shards do not masquerade as data.
5. Source aliases map only through the versioned taxonomy registry.
6. State events are deterministic, replay-safe and retain old/new values and source time.
7. Tests never send email, webhooks, exports or payment requests externally.
8. Claims cannot activate without verified account, identity, authority, current
   fingerprinted evidence and independent moderation.
9. Secrets and session credentials are not committed or stored in browser local storage.
10. Checkout, personal-data intake, export delivery, remote media and claim intake
    are false by default and require explicit gate configuration.
11. Legal unknowns are not represented as approved facts.

## Validation commands

```text
pytest -q
python -m compileall api tools incremental_update.py prepare_directory.py quality_audit.py support_quality_hook.py
cd frontend && npm audit --omit=dev && npm test && npx tsc --noEmit && npm run build
git diff --check
rg -n "quality_score" api frontend tools tests incremental_update.py prepare_directory.py quality_audit.py support_quality_hook.py
```

Integration tests requiring PostgreSQL may skip when their isolated database
fixture is unavailable; that is reported as a residual validation limit, not a pass.
