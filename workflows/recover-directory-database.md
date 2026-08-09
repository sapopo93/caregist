# Directory Database Recovery Runbook

Use this when [`/api/health/directory`](https://www.caregist.co.uk/api/health/directory) reports:

- `status: "degraded"`
- `capabilities.operatingMode: "fallback"`
- `capabilities.databaseAvailable: false`

## Current signals

- `databaseReason: "auth_failed"` means the configured Vercel DB credential is stale or invalid.
- `databaseReason: "quota_exceeded"` means Neon is reachable, but the project has exhausted compute quota.
- `databaseReason: "not_configured"` means neither `DATABASE_URL` nor `POSTGRES_URL` is present in the deployed environment.
- `databaseReason: "connection_failed"` means the DB host could not be reached reliably.

## Recovery steps

1. Confirm the public health payload:

```bash
curl -s https://www.caregist.co.uk/api/health/directory
```

2. Pull the live Vercel production env and inspect the DB vars:

```bash
vercel env pull /tmp/caregist-prod.env --environment=production
rg '^DATABASE_URL=|^POSTGRES_URL=' /tmp/caregist-prod.env
```

3. Test the current DB credential directly from the frontend runtime:

```bash
cd frontend
node - <<'NODE'
const { createPool } = require('@vercel/postgres');
require('fs').readFileSync('/tmp/caregist-prod.env', 'utf8')
  .split('\n')
  .filter(Boolean)
  .forEach((line) => {
    const index = line.indexOf('=');
    if (index > 0) {
      const key = line.slice(0, index);
      const value = line.slice(index + 1).replace(/^"|"$/g, '');
      process.env[key] = value;
    }
  });

(async () => {
  const pool = createPool({
    connectionString: process.env.POSTGRES_URL || process.env.DATABASE_URL,
  });
  try {
    const result = await pool.query('select 1 as ok');
    console.log(result.rows[0]);
  } finally {
    await pool.end();
  }
})();
NODE
```

4. If the failure is `auth_failed`, overwrite both production DB vars with the current valid Neon connection string and redeploy:

```bash
python3 - <<'PY' | vercel env add DATABASE_URL production --force --yes
for line in open('.env', 'r', encoding='utf-8'):
    if line.startswith('DATABASE_URL='):
        print(line.split('=', 1)[1].strip(), end='')
        break
PY

python3 - <<'PY' | vercel env add POSTGRES_URL production --force --yes
for line in open('.env', 'r', encoding='utf-8'):
    if line.startswith('DATABASE_URL='):
        print(line.split('=', 1)[1].strip(), end='')
        break
PY

vercel deploy --prod --yes
```

5. If the failure is `quota_exceeded`, resolve the Neon quota issue first:

- Upgrade the Neon plan, or
- Increase/reset compute quota, or
- Move the database to a plan/project with headroom.

Then redeploy production so fresh lambdas pick up the same env.

6. Verify recovery with strict DB-mode smoke:

```bash
CAREGIST_REQUIRE_DATABASE=1 python3 tools/verify-deploy.py
```

Expected result:

- `status: "ok"`
- `capabilities.operatingMode: "database"`
- `capabilities.readMode: "database"`
- `capabilities.writeMode: "database"`

7. Run an end-to-end lead/export smoke if you want proof that normal writes are back:

```bash
CAREGIST_REQUIRE_DATABASE=1 CAREGIST_LEAD_EMAIL=ops@example.com python3 tools/verify-deploy.py
```
