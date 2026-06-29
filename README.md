# CareGist CQC Directory MVP

This repository now includes a first-revenue MVP in [`frontend`](/Users/user/CareGist/frontend) built on Next.js App Router, TypeScript, Tailwind, and Postgres-backed directory search.

## Required environment variables

For the MVP deployment:

- `POSTGRES_URL`
- `STRIPE_PAYMENT_LINK_URL`
- `DIRECTORY_TOKEN_SECRET`
- `LEAD_NOTIFY_EMAIL`

Recommended for correct canonical URLs and metadata:

- `APP_URL`
- `NEXT_PUBLIC_APP_URL`

Recommended for resilient lead notifications when the database is unavailable:

- `RESEND_API_KEY`
- `ENQUIRY_FROM_EMAIL`

The production build expects the packaged full fallback dataset at [`frontend/data/directory-fallback-full.csv`](/Users/user/CareGist/frontend/data/directory-fallback-full.csv). `npm run build` now fails fast if that file is missing or clearly incomplete.

## Local development

From [`frontend`](/Users/user/CareGist/frontend):

```bash
npm install
npm run dev
```

The public routes are:

- `/`
- `/search`
- `/provider/[slug]`
- `/lead-list`
- `/api/export`

## Seed the database

The directory data should come from the PostgreSQL section of [`import_to_db.sql`](/Users/user/CareGist/import_to_db.sql), the MVP lead/export migration, and [`directory_providers.sql`](/Users/user/CareGist/directory_providers.sql).

Run these commands from the repo root:

```bash
sed -n '1,60p' import_to_db.sql | psql "$POSTGRES_URL"
psql "$POSTGRES_URL" -f db/migrations/030_directory_public_mvp.sql
psql "$POSTGRES_URL" -f directory_providers.sql
```

That creates:

- `care_providers`
- `leads`
- `export_access_tokens`

## Deploy to Vercel

1. Create or link a Vercel project with [`frontend`](/Users/user/CareGist/frontend) as the root directory.
2. Provision a Vercel Postgres database and ensure `POSTGRES_URL` is available to the project.
3. Set `STRIPE_PAYMENT_LINK_URL`, `DIRECTORY_TOKEN_SECRET`, `LEAD_NOTIFY_EMAIL`, `RESEND_API_KEY`, and `ENQUIRY_FROM_EMAIL` in Vercel project environment variables.
4. Deploy the project.
5. After deploy, run the seed commands above against the production `POSTGRES_URL` if the database-backed directory is available.
6. Run the smoke verifier against the public URL:

```bash
python3 tools/verify-deploy.py
```

The repository also includes a scheduled GitHub Actions workflow at [.github/workflows/production-smoke.yml](/Users/user/CareGist/.github/workflows/production-smoke.yml:1) that runs the same public smoke every 30 minutes and on pushes to `main`.

To require normal database mode during verification instead of accepting the protected fallback path:

```bash
CAREGIST_REQUIRE_DATABASE=1 python3 tools/verify-deploy.py
```

Optional full lead/export smoke (this sends a real lead notification email):

```bash
CAREGIST_LEAD_EMAIL=ops@example.com python3 tools/verify-deploy.py
```

The app expects the public marketing/search experience to run entirely from the Next.js frontend. No separate Python API is required for the MVP flow.

## Verification commands

From [`frontend`](/Users/user/CareGist/frontend):

```bash
npm test
npm run build
```

## Notes

- `/api/export` returns `401` without a valid token.
- The token is issued only after the lead form writes to `leads`.
- Stripe checkout is intentionally implemented with a Payment Link, not a custom checkout backend.
