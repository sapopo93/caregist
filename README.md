# Caregist

UK care provider intelligence platform. See `/workflows/` for runbooks.

## Local setup

After cloning:

```bash
bash scripts/install-hooks.sh
```

This installs the pre-commit secret scanner. Bypass with `git commit --no-verify` in emergencies.

## Documentation

- Production audit: see `PRODUCTION_AUDIT.md` (private)
- Deployment: `workflows/deploy-ec2.md`
- Backup & restore: `workflows/restore-from-snapshot.md` (added in PR 8)
- Secret rotation: `workflows/secret-rotation-stripe.md`
