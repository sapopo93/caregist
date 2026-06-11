# CareGist

UK care provider intelligence platform. Aggregates CQC public data, powers a provider directory, and delivers a new-registration feed for care-sector B2B subscribers.

## Architecture

- **CQC ETL Pipeline** (`*.py` in root) — extracts and normalises provider data from the CQC public API into PostgreSQL.
- **FastAPI backend** (`api/`) — REST API with tiered API key auth, Stripe billing, new-registration feed, and outbound webhooks.
- **Next.js frontend** (`frontend/`) — SSR directory UI and authenticated dashboard.
- **Operational tools** (`tools/`) — Python scripts for feed cycles, monitor alerts, email queue, and weekly digests.

See `CLAUDE.md` for a full architecture reference and `deploy/README.md` for the EC2 deployment runbook.

## Development

```bash
cp .env.example .env
# Fill in credentials — see comments in .env.example
docker compose up
```

## Workflows

Operational runbooks live in `workflows/`:

| Runbook | Purpose |
|---------|---------|
| `workflows/apply-migrations.md` | Apply database migrations |
| `workflows/deploy-ec2.md` | Deploy to AWS EC2 |
| `workflows/flush-email-queue.md` | Manually flush the email queue |
| `workflows/run-feed-cycle.md` | Run the new-registration feed cycle |
| `workflows/secret-rotation-stripe.md` | Rotate Stripe keys |
| `workflows/send-monitor-alerts.md` | Send provider-change monitor alerts |

---

## Legal & compliance

CareGist processes personal data under UK GDPR and the Data Protection Act 2018. The following documents must be reviewed and placeholders filled before the service takes live signups.

### Published policies (live site)

| Page | Path | Status |
|------|------|--------|
| Privacy Policy | `/privacy` (`frontend/app/privacy/page.tsx`) | Owner must fill company number, registered address, and ICO registration number |
| Terms of Service | `/terms` (`frontend/app/terms/page.tsx`) | Live — owner should arrange legal review |
| Cookie settings | `/cookie-settings` | Managed by Lattice PR (cookie banner) |

### Compliance documents (this repo)

| Document | Path | Purpose |
|----------|------|---------|
| DPIA template | `docs/compliance/dpia-template.md` | ICO-structured Data Protection Impact Assessment — owner must complete and sign before launch |
| Retention policy | `docs/compliance/retention-policy.md` | Per-data-type retention schedule and deletion procedures |
| ICO registration runbook | `workflows/ico-registration.md` | Step-by-step guide to register with the ICO and obtain a registration number |

### Owner actions before launch

1. **Register with the ICO** — follow `workflows/ico-registration.md`. Fee is £40 (Tier 1) or £60 (Tier 2). Receive registration number within 24 hours.
2. **Fill privacy policy placeholders** — open `frontend/app/privacy/page.tsx` and replace:
   - `10417923`
   - `[Company registered address — registered in Reigate; owner to fill exact street address from Companies House public record]`
   - `[ICO reg number — owner fills post-registration]`
3. **Complete and sign the DPIA** — `docs/compliance/dpia-template.md`. Get director and (if applicable) legal counsel signatures.
4. **Schedule annual ICO renewal** — see step 7 of the ICO registration runbook.

For privacy enquiries: `privacy@caregist.co.uk`.
