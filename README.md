# Caregist

**UK care provider intelligence platform.** Caregist aggregates CQC (Care Quality Commission) registration data, inspection reports, and quality ratings for every regulated care provider in England. It surfaces this data through a search and filtering interface for professionals sourcing placements, an alerting tier for providers monitoring their own ratings, and a webhook subscription API for Business-tier partners who need real-time change notifications pushed to their own systems.

---

## Table of Contents

1. [What Caregist Is](#what-caregist-is)
2. [Architecture](#architecture)
3. [Local Development Setup](#local-development-setup)
4. [Production Deployment](#production-deployment)
5. [Environment Variables](#environment-variables)
6. [Runbook & Workflow Documentation](#runbook--workflow-documentation)
7. [Legal & Compliance](#legal--compliance)
8. [License](#license)

---

## What Caregist Is

Caregist is a B2B intelligence layer on top of the CQC open data feed. Core capabilities:

- **CQC feed ingestion** — nightly and on-demand sync of the `/changes/location` CQC endpoint, with an automatic list-scan fallback when the diff endpoint is unavailable.
- **Provider search and ratings** — full-text and faceted search across CQC-registered providers, surfacing ratings, inspection dates, and recent changes.
- **Monitor alerts** — configurable email alerts when a tracked provider's rating changes or a new inspection report is published.
- **Webhook subscriptions (Business tier)** — HTTP POST delivery of provider-change events to customer-supplied endpoints, with HMAC-SHA256 signature verification.
- **Stripe billing integration** — Starter, Pro, Pro Seat, Business, and Enterprise tiers managed through Stripe Checkout and the billing portal.

---

## Architecture

```
Internet
   |
   +-- Next.js frontend (Node 22, React 19, Tailwind CSS 4)
   |      caregist-frontend  /  pnpm dev  /  npm run build
   |
   +-- FastAPI backend (Python 3.12, uvicorn, asyncpg)
          api.main:app  /  single-worker uvicorn (EC2)
          |
          +-- Neon Postgres (DATABASE_URL)
          +-- Resend (transactional email)
          +-- Stripe (billing)
          +-- Sentry (error monitoring — backend + frontend)
          +-- AWS S3 / KMS (encrypted database backups)
```

**Deployment target:** Single EC2 instance running a single-worker `uvicorn` process managed by systemd. Migrations run at deploy time via `python db/apply_migrations.py`. KMS-encrypted backups are managed by the Bedrock infrastructure layer (see `terraform/README.md`).

**Container image:** `Dockerfile` builds a `python:3.12-slim` image exposing port 8000. The EC2 host sets `$PORT`; locally it defaults to 8000.

**CI:** GitHub Actions runs on every push to `main` and on all pull requests. Backend job: `pytest` + `pip check` + `pip-audit`. Frontend job: `tsc --noEmit` + unit tests + production build + `npm audit --audit-level=high`.

---

## Local Development Setup

### Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.12 |
| Node.js | 22 |
| npm | bundled with Node 22 |
| pnpm | latest (`npm i -g pnpm`) — optional; npm also works |

### Steps

```bash
# 1. Clone
git clone https://github.com/sapopo93/caregist.git
cd caregist

# 2. Backend dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-api.txt

# 3. Frontend dependencies
cd frontend
npm install                      # or: pnpm install
cd ..

# 4. Environment variables
cp .env.example .env
# Edit .env — fill in DATABASE_URL and any keys needed for your workflow.
# See the Environment Variables section below for the full table.

# 5. Install git hooks (Mortise PR #4)
bash scripts/install-hooks.sh

# 6. Run backend tests
pytest -q

# 7. Start the frontend dev server
cd frontend
npm run dev                      # http://localhost:3000

# 8. Start the backend (separate terminal)
uvicorn api.main:app --reload --port 8000
```

The frontend proxies API calls to `http://localhost:8000` in development. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if you need to override.

---

## Production Deployment

Full deploy steps are in [`workflows/deploy-ec2.md`](workflows/deploy-ec2.md).

Infrastructure provisioning (VPC, EC2, RDS parameter groups, KMS key, S3 backup bucket) is documented in [`terraform/README.md`](terraform/README.md) (Bedrock PR #3).

**Key deploy facts:**
- Single-worker `uvicorn`; do not add `--workers N` without benchmarking connection-pool sizing against `asyncpg`.
- Migrations are applied automatically at deploy time. For manual migration runs, see [`workflows/apply-migrations.md`](workflows/apply-migrations.md).
- The production `.env` lives at `/home/caregist/CareGist/.env` on the EC2 host.

---

## Environment Variables

Copy `.env.example` for the full annotated list. The table below covers the variables that must be set for any production or staging environment.

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | Neon Postgres connection string (`postgresql+asyncpg://...`) |
| `API_MASTER_KEY` | Yes | Internal API authentication key |
| `RESEND_API_KEY` | Yes | Resend transactional email API key |
| `STRIPE_SECRET_KEY` | Yes | Stripe live secret key (`sk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE_PRICE_STARTER` | Yes | Stripe Price ID for Starter plan |
| `STRIPE_PRICE_PRO` | Yes | Stripe Price ID for Pro plan |
| `STRIPE_PRICE_PRO_SEAT` | Yes | Stripe Price ID for Pro Seat add-on |
| `STRIPE_PRICE_BUSINESS` | Yes | Stripe Price ID for Business plan |
| `STRIPE_PRICE_ALERTS_PRO` | Yes | Stripe Price ID for Alerts Pro add-on |
| `STRIPE_PRICE_PROFILE_ENHANCED` | Yes | Stripe Price ID for Enhanced profile |
| `STRIPE_PRICE_PROFILE_PREMIUM` | Yes | Stripe Price ID for Premium profile |
| `STRIPE_PRICE_PROFILE_SPONSORED` | Yes | Stripe Price ID for Sponsored profile |
| `STRIPE_PRICE_ENTERPRISE` | Yes | Stripe Price ID for Enterprise plan |
| `APP_URL` | Yes | Public base URL (e.g. `https://caregist.co.uk`) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins for CORS |
| `WEBHOOK_SECRET_KEY` | Yes | HMAC key for Business-tier webhook signatures |
| `ENQUIRY_FROM_EMAIL` | Yes | From-address for enquiry confirmation emails |
| `MONITOR_ALERT_FAILURE_EMAIL` | Yes | Alert email for feed/monitor failures |
| `SUPPORT_PLATFORM_URL` | No | URL for the internal support platform |
| `CAREGIST_TO_SUPPORT_TOKEN` | No | Auth token for support platform integration |
| `SUPPORT_INTERNAL_TOKEN` | No | Internal token for support API calls |
| `SENTRY_DSN` | No | Sentry DSN for backend error monitoring |

See `.env.example` for the canonical, annotated list.

---

## Runbook & Workflow Documentation

All operational runbooks live in [`workflows/`](workflows/).

### Existing runbooks

| Runbook | Description |
|---|---|
| [`workflows/deploy-ec2.md`](workflows/deploy-ec2.md) | Full production deploy procedure — SSH, env update, service restart, health check |
| [`workflows/apply-migrations.md`](workflows/apply-migrations.md) | How to apply database migrations manually or verify automatic migration at deploy time |
| [`workflows/run-feed-cycle.md`](workflows/run-feed-cycle.md) | Manually trigger a CQC feed ingestion cycle; monitor progress and validate results |
| [`workflows/flush-email-queue.md`](workflows/flush-email-queue.md) | Flush or inspect the outbound email queue |
| [`workflows/send-monitor-alerts.md`](workflows/send-monitor-alerts.md) | Manually run the monitor-alerts tool and interpret its output |
| [`workflows/secret-rotation-stripe.md`](workflows/secret-rotation-stripe.md) | Rotate Stripe API secret key and webhook signing secret (Cog PR #1) |

### New runbooks (this PR)

| Runbook | Description |
|---|---|
| [`workflows/incident-response.md`](workflows/incident-response.md) | Severity classification, on-call escalation, comms templates, post-mortem format |
| [`workflows/secret-rotation-resend.md`](workflows/secret-rotation-resend.md) | Rotate the Resend API key with zero email downtime |
| [`workflows/secret-rotation-sentry.md`](workflows/secret-rotation-sentry.md) | Rotate the Sentry DSN |
| [`workflows/secret-rotation-webhook-key.md`](workflows/secret-rotation-webhook-key.md) | Rotate `WEBHOOK_SECRET_KEY` — generate new keypair, re-encrypt stored data, deploy, revoke old |
| [`workflows/webhook-debugging.md`](workflows/webhook-debugging.md) | Debug Business-tier webhook delivery failures — logs, signature, retries, common causes |
| [`workflows/stuck-email-recovery.md`](workflows/stuck-email-recovery.md) | Manually unstick stuck emails, requeue failures, extract from DLQ, force-resend |
| [`workflows/cqc-fallback-activation.md`](workflows/cqc-fallback-activation.md) | Activate and monitor the CQC list-scan fallback when `/changes/location` is unavailable |

---

## Legal & Compliance

> This section was added by Vellum PR #10. Do not remove or significantly modify without reviewing that PR's rationale.

- **Data source:** All provider data originates from the CQC open data feed published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Caregist does not claim ownership of CQC-sourced data.
- **GDPR / UK GDPR:** Caregist processes personal data (names, email addresses, billing information) on behalf of its subscribers. A Data Processing Agreement (DPA) is available on request at `legal@caregist.co.uk`.
- **PCI DSS:** Caregist does not store card data. Payment card processing is handled exclusively by Stripe. Caregist operates as a PCI SAQ A merchant.
- **CQC Terms of Use:** Usage of the CQC open data API must comply with [CQC Terms of Use](https://www.cqc.org.uk/about-us/transparency/using-cqc-data). Automated access must respect rate limits and attribution requirements.
- **Webhooks and data onward transfer:** Business-tier customers receiving webhook payloads containing provider data are responsible for their own GDPR compliance regarding any further processing or storage of that data.

---

## License

> **Owner action required.** No `LICENSE` file currently exists in this repository.
>
> Recommended options:
> - **MIT** — permissive; suitable if you intend to allow commercial use, forks, and third-party integrations without restriction.
> - **AGPL-3.0** — copyleft; suitable if you want to require that any modifications served over a network also be open-sourced (protects the SaaS use case).
>
> To add a license: create a `LICENSE` file in the repo root containing the full text of your chosen licence, and update this section accordingly. GitHub's licence picker at **Insights → Community → License** can generate the correct text.
