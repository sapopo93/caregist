# CareGist

CareGist is a UK care-provider directory and intelligence service built from Care Quality Commission data. The **controlled catalogue-safety release is deployed**, but the paid Radar release is not yet approved. Checkout, source collectors, outbound delivery, and other commercial capabilities remain fail-closed until their named recovery, source-trust, legal, and pilot gates pass. A configured vendor credential is not approval to enable a capability.

The live site at https://www.caregist.co.uk serves the Free Directory, provider detail pages, the final Radar/Feed positioning, source-status reporting, and the current legal and licence surfaces. It does not publicly sell legacy data packs, paid listings, extra seats, or predictive products. The live Stripe catalogue contains Radar Regional (£299/month), Radar National (£799/month), Intelligence Feed Pilot (£6,000/year), and quote-only Embedded Enterprise; the three priced products remain checkout-gated. Production contains 56,743 location rows, of which 56,742 are active.

Production Neon is on Launch with an evidenced seven-day history window. A point-in-time restore drill, an isolated migration rehearsal, and the production migration chain through `049_cqc_signal_intelligence.sql` passed with provider counts preserved. The recovery branch remains retained. Source collectors may now enter shadow mode, but paid checkout and outbound delivery remain blocked until the seven-day source-trust, legal, billing-lifecycle, and private-pilot gates pass.

## Production architecture

The canonical deployment is the multi-service configuration in `vercel.json`:

- **Vercel frontend:** Next.js App Router in `frontend/` serves public directory, account, and dashboard routes.
- **Vercel backend:** FastAPI in `api/` serves `/api/v1/*`, internal tasks, health, metrics, billing, and webhooks.
- **Neon Postgres:** the Launch production project holds the directory, event ledger, reconciliation state, accounts, and billing evidence. Isolated branches provide restore drills and migration rehearsal; no separate staging URL is configured in the local operator environment.
- **Redis:** shared rate limits and runtime coordination. Production must not rely on the in-process fallback.
- **Stripe, Resend, and Sentry:** billing, transactional/operational email, and error telemetry respectively. Their capabilities remain gated until the corresponding release evidence is approved.

Vercel binds the backend service URL to the frontend as `CAREGIST_BACKEND_URL`. Public `/api/v1/*` requests are routed to FastAPI; frontend-owned routes such as `/api/health/directory` remain in Next.js. The old EC2/PM2 instructions are historical and are not a production deployment path.

## Safe defaults

Checkout, monitoring activation, exports, leads, claims, reviews, enquiries, outbound delivery, remote media, and outbound communications are governance-controlled. Their production and preview defaults are `false`; enabling any one requires its named approval, denial-path tests, monitoring, and rollback evidence. A configured vendor credential is not approval to enable a capability.

## Developer bootstrap

Install Python 3.12 and Node.js 22, then run from the repository root:

```bash
./scripts/bootstrap-dev.sh
```

The command creates `.venv` with the same Python minor version as CI, installs backend/test/audit dependencies, validates dependency resolution, and installs the locked frontend dependencies.

Run the local gates with:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check api/ tools/ db/ tests/
npm --prefix frontend test
npm --prefix frontend run build
```

Required runtime values are documented in `DEPLOYMENT_CHECKLIST.md`. Keep secrets in the approved environment/secret manager; never commit `.env` or `.projects` state.

## Database and migrations

Apply migrations to local or staging environments with `db/apply_migrations.py`. Production migrations require an evidenced Neon recovery point and the explicit production confirmation flag:

```bash
.venv/bin/python db/apply_migrations.py --target staging
.venv/bin/python db/apply_migrations.py --target production --confirm-production-backup
```

Migrations are forward-only in production: prefer additive expand/contract changes, use a corrective migration for isolated defects, and use Neon point-in-time recovery only for destructive or irrecoverable changes. The two already-applied `034` files are a frozen historical exception. Do not rename them; all future migration numbers must be unique. See `db/migrations/README.md` and `workflows/apply-migrations.md`.

## Reconciliation and freshness

CQC reconciliation is prepared from one immutable snapshot, processed by deterministic shards, and finalized before the authoritative watermark advances. The scheduled reconciliation must remain disabled until a complete manual production batch passes its count, coverage, checksum, and watermark gates.

Operational endpoints:

- `/api/v1/health/liveness` — process liveness only
- `/api/v1/health/readiness` — traffic dependencies; intentionally separate from source freshness
- `/api/v1/health/freshness` — source watermark and derived-feed freshness
- `/api/v1/version` — deployed Git SHA for exact-release verification
- `/api/health/directory` — frontend directory mode and deployed Git SHA
- `/data-status` — public source-watermark status

The 15-minute freshness watchdog records deduplicated state in Postgres and notifies `ops@caregist.co.uk`. Preview and production smoke tests compare the deployed SHA with the tested commit and verify `/data-status` and provider sitemaps.

## Recovery and release

Neon-native PITR is the sole database recovery strategy. A seven-day restore window is a release prerequisite. The production resource was verified through the provider integration as Free on 9 August 2026 and therefore cannot meet this gate. Upgrade production to Launch, configure and evidence the full seven-day window, and create a recorded recovery point before any production migration. Monthly drills restore to an isolated branch, run schema/count invariants, record RPO/RTO, and delete the temporary branch only after approval.

Use these documents:

- `DEPLOYMENT_CHECKLIST.md` — authoritative release gates
- `workflows/neon-pitr-restore-drill.md` — recovery procedure and evidence requirements
- `ops/alert-catalog.yaml` — required monitoring signals and ownership
- `ops/evidence/alert-test-template.md` — alert-channel test evidence
- `PRODUCTION_READY.md` — historical readiness claim retained for audit only

## Public smoke verification

```bash
CAREGIST_APP_URL=https://preview.example.invalid \
CAREGIST_EXPECTED_GIT_SHA="$(git rev-parse HEAD)" \
python3 tools/verify-deploy.py
```

The verifier checks release identity, directory health, `/data-status`, provider sitemaps, search, provider rendering, and export denial. Set `CAREGIST_REQUIRE_DATABASE=1` for release acceptance. Lead/export mutation smoke is opt-in because it can generate persisted records and notifications.
