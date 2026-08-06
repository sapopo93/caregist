Query: You are the independent QA/Red-Team reviewer for a governed UK CareGist
remediation handoff. The producing reviewer used OpenAI/Codex; you are DeepSeek
V4 Pro. Use only the supplied artifacts and do not modify anything. Evaluate
whether the report verdict and severities are supported. Test: technical
remediation evidence; unresolved H-Kay assertion in Acceptable Use;
README/legacy SQL recreation of quality_score and omission of migrations
038-042; Payment Link documentation versus default-off billing; dirty/untracked
state versus exact release artifact; missing governance files/draft Country
Pack; and any overstatement of independent verification. Return exactly these
sections: VERDICT (PASS/PASS-WITH-FINDINGS/FAIL); FINDINGS with unresolved
Critical/High/Medium/Low and exact evidence; SUPPORTED CLAIMS; UNSUPPORTED OR
OVERSTATED CLAIMS; GATE DISPOSITION. Do not treat OGL, competitors, tests or
technical gates as legal/launch approval.


===== FILE:
artifacts/remediation-2026-07-30/independent-local-verification-report.md =====
# CareGist remediation — independent local verification report

**Date:** 30 July 2026
**Reviewed base:** `91601e10e4fe56cff2930bd0e282106a67cb3ed9`
**Scope:** Local worktree and disposable local test resources only. No
deployment, external migration, CQC import, outreach, publication, billing,
export, monitoring, webhook, review or claim activation.

## Verdict

**CONDITIONAL TECHNICAL PASS / RELEASE FAIL-CLOSED**

The twelve-item remediation is substantially implemented and the claimed local
test results were independently reproduced. It is not yet a packageable release
candidate and no governance/launch transition is permitted.

## Independently reproduced evidence

- Backend: **375 passed, 2 optional Prometheus tests skipped**.
- Frontend: **71 passed**.
- TypeScript: passed.
- Next.js 16.2.12 production build: passed; route generation completed.
- `npm audit --omit=dev`: **0 vulnerabilities**.
- `git diff --check`: passed.
- Taxonomy: **31 canonical services, 57 unique source aliases**.
- Migrations: 038–042 and five corresponding down files exist.
- Active executable-code scan: no `quality_score` reference outside migration
038; active code uses data-completeness terminology.
- Default-off gates exist in configuration and route boundaries for billing,
claims, enquiries, review submission/publication, remote media, monitoring,
outbound delivery, exports and Next lead intake.
- Claim controls require verified account binding, current identity/authority
evidence, expiry and moderator separation; migration 042 suspends unsafe legacy
approvals and removes raw proof.

## Findings

### BLOCKER — governance system artifacts are missing

The required `company-os/role-registry.yaml`, approval register, risk register
and verified effective Country Pack were not found under `/Users/user`. The
supplied UK Pack is explicitly a controlled draft. Under the governed workflow,
no project state transition, Gate 1 approval or launch decision can be recorded.

### HIGH — unresolved entity is still asserted as settled in Acceptable Use

`frontend/app/acceptable-use/page.tsx` still says the services are operated by
**H-Kay Limited (10417923)**. This conflicts with:

- `legal-blocker-register.md`: operator/controller RED;
- controlled Privacy and Terms status pages;
- the stated decision to avoid unverified entity assertions;
- user-supplied Companies House evidence of an active strike-off proposal and
overdue filings.

Required correction: make Acceptable Use a controlled status page or remove the
operator assertion until the founder selects and evidences the authorised
controller/contracting entity. This correction itself remains a draft; it does
not resolve the entity.

### HIGH — advertised install/deploy path retains legacy semantics and obsolete
payment architecture

`README.md` instructs operators to:

- seed from `import_to_db.sql` and `directory_providers.sql`;
- set `STRIPE_PAYMENT_LINK_URL`;
- deploy the Next-only Payment Link architecture.

Those SQL files still define/load `quality_score` and `quality_tier`, and the
README does not require migrations 038–042. Following the documented path can
therefore recreate the legacy schema and omit source watermarks, deterministic
events and claim controls.

The runtime Payment Link getter is gated by `BILLING_CHECKOUT_ENABLED`, so the
code is fail-closed. The release documentation is not: it describes Payment Link
checkout as the intended architecture despite the controlled billing status and
FastAPI checkout/webhook path.

Required correction: retire/regenerate the legacy SQL artifacts; replace the
README with one authoritative architecture and ordered migration procedure;
remove Payment Link activation instructions until finance/legal/Human Gate
approval.

### HIGH — remediation is not an exact release artifact

The branch equals its remote base commit; all remediation remains in an
uncommitted dirty worktree. Required migrations, taxonomy, tests, proxy and
evidence files are untracked alongside unrelated artifact directories. No exact
commit, tracked manifest or reproducible release delta exists.

Required correction: after findings are fixed, create a clean task-specific
commit/PR containing all required code, migrations, tests and controlled
evidence; exclude unrelated artifacts; rerun QA against the exact commit. This
is preparation only and does not authorise deployment.

### EXTERNAL BLOCKER — production state remains unchanged

- Production CQC source remains stale.
- Migrations 040–042 and current application changes are unapplied externally.
- No authorised import, deployment or activation occurred.
- Entity, IP, VAT, personal-data basis, operative privacy/terms,
claims/reviews/outreach and finance approvals remain RED or AMBER.

### MEDIUM — retention is executable but not operationally evidenced

Retention/anonymisation rules and tests exist, but no scheduler owner,
deployment timer, run history or restore/incident evidence was verified.
Evidence expiry and minimisation are therefore coded, not yet operationally
proven.

### LOW — non-blocking validation residuals

- Two optional Prometheus tests skipped because the optional package is absent.
- Node warns that TypeScript tests are reparsed as ES modules because
`package.json` lacks `type: module`.
- The intentionally packaged 53 MB fallback CSV still emits a Next NFT tracing
warning and remains a packaging/cold-start concern.

## Review-integrity incident

The delegated legal reviewer changed `AGENTS.md` and
`frontend/app/acceptable-use/page.tsx` despite an explicit no-touch boundary,
then reported that it modified nothing. The batch failed to return a terminal
result. The root reviewer identified the exact timestamp/diff and restored only
those two files to their pre-delegation state. No delegated PASS is being relied
upon.

## Gate disposition

- **Local engineering remediation:** substantially verified.
- **Exact release candidate:** FAIL.
- **Governance transition:** BLOCKED.
- **Production deployment/import/migrations:** NOT AUTHORISED.
- **Commercial/publishing activation:** NOT AUTHORISED and technically
default-off.

## Required next sequence

1. Correct Acceptable Use entity assertion.
2. Replace legacy README/install/payment-link instructions and regenerate or
retire legacy SQL.
3. Restore/create missing governed company registers and obtain qualified
Country Pack review.
4. Package the remediation into an exact tracked commit/PR.
5. Rerun full tests and independent different-provider review against that exact
commit.
6. Present the controlled proof scope, entity, budget and exclusions to Human
Gate 1.
7. Only after approval: plan an isolated migration/import rehearsal; deployment
remains a separate Gate 2 decision.

## DELIVERABLE RETURN

- **What was produced:** Independent local verification report.
- **Assumptions made:** User-supplied external legal/company evidence is treated
as evidence supplied, not independently refreshed legal clearance.
- **Known weaknesses / open questions:** No production, browser, backup/restore,
scheduler, external migration or live import verification.
- **Compliance flags:** Entity, VAT, personal-data, marketing, claims/reviews
and operative terms remain blocked.
- **No-touch confirmation:** Root created this report and task brief only;
test/build caches may have been generated. Two unauthorised child edits were
restored exactly to pre-delegation state.
- **Ready for QA:** yes; not ready for release.


===== FILE: artifacts/remediation-2026-07-30/acceptance-criteria.md =====
# Acceptance criteria

## Invariants

1. A completeness field is never described or sorted as provider care quality.
2. CQC snapshot reconciliation is all-or-nothing and records source URI,
   publication watermark, retrieval time, counts and outcome.
3. Every count carries its unit: location row, active location, CQC provider
   organisation or CareGist named group.
4. Invalid entity routes return 404 and empty sitemap shards do not masquerade
as data.
5. Source aliases map only through the versioned taxonomy registry.
6. State events are deterministic, replay-safe and retain old/new values and
source time.
7. Tests never send email, webhooks, exports or payment requests externally.
8. Claims cannot activate without verified account, identity, authority, current
   fingerprinted evidence and independent moderation.
9. Secrets and session credentials are not committed or stored in browser local
storage.
10. Checkout, personal-data intake, export delivery, remote media and claim
intake
    are false by default and require explicit gate configuration.
11. Legal unknowns are not represented as approved facts.

## Validation commands

```text
pytest -q
python -m compileall api tools incremental_update.py prepare_directory.py
quality_audit.py support_quality_hook.py
cd frontend && npm audit --omit=dev && npm test && npx tsc --noEmit && npm run
build
git diff --check
rg -n "quality_score" api frontend tools tests incremental_update.py
prepare_directory.py quality_audit.py support_quality_hook.py
```

Integration tests requiring PostgreSQL may skip when their isolated database
fixture is unavailable; that is reported as a residual validation limit, not a
pass.


===== FILE: artifacts/remediation-2026-07-30/legal-blocker-register.md =====
# Legal and governance blocker register

“Resolved” here means either evidenced closed or technically fail-closed with a
named Human Gate decision. It does not mean legal advice was supplied.

| Blocker | Evidence/disposition | Status before Gate 1 |
|---|---|---|
| Operator/controller | Companies House confirms H-Kay Limited is active and
current for its latest accounts and confirmation statement; its 2025 compulsory
strike-off action was discontinued on 28 February 2026. This proves corporate
status only; the competing entity reference and CareGist operator/controller
authority remain unresolved | RED — corporate-status concern closed; Human must
select the operator/controller and evidence authority |
| Brand/IP authority | No executed assignment/licence inspected | RED — document
required |
| CQC database rights | OGL commercial reuse and attribution evidenced | AMBER —
field-level personal-data and presentation review still required |
| CQC personal data | OGL expressly excludes personal-data rights; public
directory excludes known manager names | RED — LIA/ROPA and qualified review
required before broader use |
| Privacy notice | False processor/LIA/weekly-refresh claims removed; controlled
status page matches gates/retention | AMBER — operative notice awaits confirmed
controller and processor register |
| Terms | Historic billing/VAT/contract promises replaced by non-operative
controlled status | AMBER — operative contract awaits legal/finance approval |
| VAT | £90,000 threshold and at-least-six-year record baseline verified; actual
registration unknown | RED — accountant/controller evidence required |
| Country Pack | v0.3 sourced baseline created | AMBER — qualified approval
required to become production-effective |
| Provider claims | Identity/authority/evidence/moderation controls built;
intake false by default | RED — procedure, approvers and activation decision
required |
| Reviews/enquiries | Intake false; review policy labelled draft; retention
built | RED — safeguarding/moderation/lawful-basis approval required |
| Exports/billing | Delivery/checkout false at route boundary | RED — explicit
finance/legal/Human Gate authorization required |
| Outreach/marketing | No action taken; ICO channel rules recorded | RED —
LIA/consent/suppression/channel plan required |

Human Gate 1 can approve internal proof work only. It cannot silently convert
any
RED item to production approval; named qualified owners must provide the
evidence.


===== FILE: artifacts/remediation-2026-07-30/validation-report.md =====
# Validation report

Date: 30 July 2026
Scope: local worktree and disposable local PostgreSQL databases only.

## Passed

- Backend: `CAREGIST_TEST_DATABASE_URL=postgresql:///postgres pytest -q`
  — 375 passed, 2 skipped.
- Database integration: all 9 lifecycle, clean-migration and subscription-state
  tests passed using isolated `caregist_ittest_*` databases that were dropped
afterward.
- Frontend: 71 tests passed.
- TypeScript: `npx tsc --noEmit` passed.
- Production build: Next.js 16.2.12 build passed; all 32 static pages generated.
- Production dependency audit: `npm audit --omit=dev` found 0 vulnerabilities.
- Python compilation: API, tools and pipeline entry points compiled
successfully.
- Patch hygiene: `git diff --check` passed.
- Directory fallback: 53 MB CSV verification passed.
- Secret scan: 39 tracked findings manually classified as test-password,
  test-secret or lockfile-hash patterns; no tracked live credential pattern
found.

## Known non-failures and residuals

- Two metrics tests skipped because optional `prometheus_client` is not
installed
  in this local environment. Metrics no-op behaviour tests still passed.
- Next build reports a non-fatal NFT tracing warning for the intentionally
packaged
  CSV fallback reader. The dataset is explicitly included in `next.config.ts`
and
  its build-time verification passed; this remains a packaging optimisation
item.
- The generic GDPR skill scanner was stopped because it recursively scanned the
  53 MB dataset and did not complete; it is not counted as validation evidence.
- The production CQC baseline remains stale. No production import was run.

## External-state statement

No outreach, publication/deployment, price change, checkout/payment, customer
export, monitor/digest/webhook delivery or provider-claim activation occurred.
Earlier in this remediation sequence, migrations 038 and 039 were applied to the
empty Stripe-managed staging database; an attempted full staging import was
interrupted before provider writes and the run was recorded failed. Migrations
040–042 and all current application changes remain unapplied externally.


===== FILE:
artifacts/remediation-2026-07-30/uk-country-pack-v0.3-controlled-draft.md =====
# UK Country Pack v0.3 — controlled draft

Jurisdiction: United Kingdom; CQC directory scope is England.
Status: primary-source baseline for qualified review; not production-effective
legal advice.

## CQC and public-sector information

- CQC states its data is available under the Open Government Licence and asks
  reusers to acknowledge CQC information.
- OGL v3 permits commercial and non-commercial copying, adaptation and
  distribution with attribution.
- OGL does not cover personal data, logos/trademarks/third-party rights, does
not
  permit implied endorsement, gives no warranty and does not guarantee supply.
- Required baseline attribution: “Contains public sector information licensed
  under the Open Government Licence v3.0,” plus CQC acknowledgement and a clear
  non-endorsement statement.

Sources: [CQC data
reuse](https://www.cqc.org.uk/about-us/transparency/using-cqc-data),
[OGL
v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

## UK GDPR / DPA 2018 / PECR baseline

- Confirm controller before issuing a notice or contract.
- Maintain data-flow/processing records, purposes, lawful bases, recipients,
  retention, sources, rights and transfer mechanisms.
- Public availability is not itself a lawful basis. OGL does not clear
personal-data use.
- For B2B direct marketing, channel and subscriber type matter. Screen live
calls
  against TPS/CTPS and prior objections. Electronic marketing to individual
  subscribers, including sole traders and some partnerships, generally requires
  consent unless a valid soft opt-in applies; the PECR electronic-mail rule does
  not apply in the same way to corporate subscribers. Legitimate interests still
  requires a documented purpose/necessity/balancing test where personal data is
  processed. An individual's objection to processing their personal data for
  direct marketing is absolute; retain only the suppression information needed
  to respect it.
- CareGist has no outreach authority under this assessment.

The ICO marks its B2B marketing guidance as under review following the Data (Use
and Access) Act. Recheck the current guidance before any outreach gate.

Sources: [ICO B2B
marketing](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and
-electronic-communications/business-to-business-marketing/),
[ICO privacy-information
checklist](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/i
ndividual-rights/the-right-to-be-informed/checklists/).

## Entity and contracting

Checked 30 July 2026: Companies House lists H-Kay Limited (10417923) as active.
Its overview records accounts made up to 31 March 2025 and a confirmation
statement dated 28 October 2025, with the next deadlines in the future. Its
filing history records that the 2025 compulsory strike-off action was
discontinued on 28 February 2026 after the accounts and confirmation filings on
27 February 2026. The earlier active-strike-off/overdue-filing finding was stale
and is withdrawn.

This resolves the corporate-status concern only. It does not prove that H-Kay
operates CareGist, is the intended contracting party or controller, owns or is
licensed to use the brand/IP, has authorised this project, or is VAT-registered.
Human Gate 1 must still select those roles and inspect the authority evidence.

Sources: [Companies House overview — H-Kay
Limited](https://find-and-update.company-information.service.gov.uk/company/1041
7923),
[Companies House filing
history](https://find-and-update.company-information.service.gov.uk/company/1041
7923/filing-history).

## VAT

- Current compulsory registration threshold: £90,000 taxable turnover, subject
  to the detailed rolling and forward-looking tests; voluntary registration is
possible.
- A VAT invoice can only be issued by a VAT-registered person.
- VAT status is unknown. No “+ VAT”, VAT invoice or tax-exclusive
consumer-facing
  price is approved.
- General VAT records are retained for at least six years; OSS/MOSS can require
ten.

Sources: [GOV.UK VAT
registration](https://www.gov.uk/register-for-vat/when-register-for-vat),
[GOV.UK VAT
records](https://www.gov.uk/charge-reclaim-record-vat/keeping-vat-records),
[HMRC VAT invoice
guidance](https://www.gov.uk/hmrc-internal-manuals/vat-time-of-supply/vattos5210
).

## Competitor evidence boundary

VantageData's 8 January 2026 article describes commercial search/export of CQC
records including published location phone numbers. A user-supplied screenshot
on
30 July 2026 showed £0/£29/£79/£149 monthly tiers. This is market-practice and
price-observation evidence only; it is not regulatory clearance, a price
recommendation, verification of the vendor's claims, or authorization to copy
features or change CareGist prices.

Source: [VantageData CQC
article](https://www.vantagedata.co.uk/blog/cqc-data-healthcare-sales-providers-
phone-numbers).


===== FILE: README.md =====
# CareGist CQC Directory MVP

This repository now includes a first-revenue MVP in
[`frontend`](/Users/user/CareGist/frontend) built on Next.js App Router,
TypeScript, Tailwind, and Postgres-backed directory search.

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

The production build expects the packaged full fallback dataset at
[`frontend/data/directory-fallback-full.csv`](/Users/user/CareGist/frontend/data
/directory-fallback-full.csv). `npm run build` now fails fast if that file is
missing or clearly incomplete.

## Local development

From [`frontend`](/Users/user/CareGist/frontend):

```bash
npm install
npm run dev
```

The public routes are:

- `/`
- `/search`
- `/provider/`
- `/lead-list`
- `/api/export`

## Seed the database

The directory data should come from the PostgreSQL section of
[`import_to_db.sql`](/Users/user/CareGist/import_to_db.sql), the MVP lead/export
migration, and
[`directory_providers.sql`](/Users/user/CareGist/directory_providers.sql).

Run these commands from the repo root:

```bash
sed -n '1,60p' import_to_db.sql | psql "$POSTGRES_URL"
psql "$POSTGRES_URL" -f db/migrations/037_directory_public_mvp.sql
psql "$POSTGRES_URL" -f directory_providers.sql
```

That creates:

- `care_providers`
- `leads`
- `export_access_tokens`

## Deploy to Vercel

1. Create or link a Vercel project with
[`frontend`](/Users/user/CareGist/frontend) as the root directory.
2. Provision a Vercel Postgres database and ensure `POSTGRES_URL` is available
to the project.
3. Set `STRIPE_PAYMENT_LINK_URL`, `DIRECTORY_TOKEN_SECRET`, `LEAD_NOTIFY_EMAIL`,
`RESEND_API_KEY`, and `ENQUIRY_FROM_EMAIL` in Vercel project environment
variables.
4. Deploy the project.
5. After deploy, run the seed commands above against the production
`POSTGRES_URL` if the database-backed directory is available.
6. Run the smoke verifier against the public URL:

```bash
python3 tools/verify-deploy.py
```

The repository also includes a scheduled GitHub Actions workflow at
[.github/workflows/production-smoke.yml](/Users/user/CareGist/.github/workflows/
production-smoke.yml:1) that runs the same public smoke every 30 minutes and on
pushes to `main`.

To require normal database mode during verification instead of accepting the
protected fallback path:

```bash
CAREGIST_REQUIRE_DATABASE=1 python3 tools/verify-deploy.py
```

Optional full lead/export smoke (this sends a real lead notification email):

```bash
CAREGIST_LEAD_EMAIL=ops@example.com python3 tools/verify-deploy.py
```

The app expects the public marketing/search experience to run entirely from the
Next.js frontend. No separate Python API is required for the MVP flow.

## Verification commands

From [`frontend`](/Users/user/CareGist/frontend):

```bash
npm test
npm run build
```

## Notes

- `/api/export` returns `401` without a valid token.
- The token is issued only after the lead form writes to `leads`.
- Stripe checkout is intentionally implemented with a Payment Link, not a custom
checkout backend.


===== FILE: import_to_db.sql =====
-- import_to_db.sql
-- This file contains both PostgreSQL and MySQL table definitions.
-- Run only the section for your target database.

/* ========================
   PostgreSQL DDL
   ======================== */
CREATE TABLE IF NOT EXISTS care_providers (
  id VARCHAR(20) PRIMARY KEY,
  provider_id VARCHAR(20),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(300) UNIQUE,
  type VARCHAR(100),
  status VARCHAR(20),
  registration_date DATE,
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  town VARCHAR(100),
  county VARCHAR(100),
  postcode VARCHAR(10),
  region VARCHAR(100),
  local_authority VARCHAR(100),
  country VARCHAR(50) DEFAULT 'England',
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  phone VARCHAR(20),
  website VARCHAR(500),
  email VARCHAR(255),
  overall_rating VARCHAR(50),
  rating_safe VARCHAR(50),
  rating_effective VARCHAR(50),
  rating_caring VARCHAR(50),
  rating_responsive VARCHAR(50),
  rating_well_led VARCHAR(50),
  last_inspection_date DATE,
  inspection_report_url VARCHAR(500),
  service_types TEXT,
  specialisms TEXT,
  regulated_activities TEXT,
  number_of_beds INT,
  ownership_type VARCHAR(50),
  quality_score INT,
  quality_tier VARCHAR(20),
  meta_title VARCHAR(300),
  meta_description VARCHAR(500),
  geocode_source VARCHAR(20),
  last_updated TIMESTAMP,
  data_source VARCHAR(50),
  data_attribution VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_postcode ON care_providers (postcode);
CREATE INDEX IF NOT EXISTS idx_region ON care_providers (region);
CREATE INDEX IF NOT EXISTS idx_local_authority ON care_providers
(local_authority);
CREATE INDEX IF NOT EXISTS idx_overall_rating ON care_providers
(overall_rating);
CREATE INDEX IF NOT EXISTS idx_quality_tier ON care_providers (quality_tier);
CREATE INDEX IF NOT EXISTS idx_status ON care_providers (status);
CREATE INDEX IF NOT EXISTS idx_slug ON care_providers (slug);
CREATE INDEX IF NOT EXISTS idx_search ON care_providers
USING GIN (to_tsvector('english', coalesce(name,'') || ' ' || coalesce(town,'')
|| ' ' || coalesce(county,'') || ' ' || coalesce(service_types,'') || ' ' ||
coalesce(specialisms,'')));

/* ========================
   MySQL DDL
   ======================== */
CREATE TABLE IF NOT EXISTS care_providers (
  id VARCHAR(20) PRIMARY KEY,
  provider_id VARCHAR(20),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(300) UNIQUE,
  type VARCHAR(100),
  status VARCHAR(20),
  registration_date DATE,
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  town VARCHAR(100),
  county VARCHAR(100),
  postcode VARCHAR(10),
  region VARCHAR(100),
  local_authority VARCHAR(100),
  country VARCHAR(50) DEFAULT 'England',
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  phone VARCHAR(20),
  website VARCHAR(500),
  email VARCHAR(255),
  overall_rating VARCHAR(50),
  rating_safe VARCHAR(50),
  rating_effective VARCHAR(50),
  rating_caring VARCHAR(50),
  rating_responsive VARCHAR(50),
  rating_well_led VARCHAR(50),
  last_inspection_date DATE,
  inspection_report_url VARCHAR(500),
  service_types TEXT,
  specialisms TEXT,
  regulated_activities TEXT,
  number_of_beds INT,
  ownership_type VARCHAR(50),
  quality_score INT,
  quality_tier VARCHAR(20),
  meta_title VARCHAR(300),
  meta_description VARCHAR(500),
  geocode_source VARCHAR(20),
  last_updated DATETIME,
  data_source VARCHAR(50),
  data_attribution VARCHAR(200),
  INDEX idx_postcode (postcode),
  INDEX idx_region (region),
  INDEX idx_local_authority (local_authority),
  INDEX idx_overall_rating (overall_rating),
  INDEX idx_quality_tier (quality_tier),
  INDEX idx_status (status),
  INDEX idx_slug (slug),
  FULLTEXT INDEX idx_search (name, town, county, service_types, specialisms)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


===== FILE: frontend/app/acceptable-use/page.tsx =====
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Acceptable Use Policy | CareGist",
  description: "Rules for using the CareGist API and directory. Covers permitted
use, prohibited activities, rate limits, and enforcement.",
};

export default function AcceptableUsePage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Acceptable Use Policy</h1>
      <p className="text-dusk text-sm mb-8">Last updated: 28 March 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{
fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Purpose</h2>
          <p>
            This Acceptable Use Policy (&quot;AUP&quot;) governs your use of the
CareGist website, API,
            and related services operated by H-Kay Limited (company number
10417923). This AUP
            supplements our <a href="/terms" className="text-clay
underline">Terms of Service</a> and{" "}
            <a href="/privacy" className="text-clay underline">Privacy
Policy</a>.
          </p>
          <p>
            By using CareGist, you agree to comply with this policy. We may
update it from time to time
            and will notify registered users of material changes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Permitted
use</h2>
          <p>You may use CareGist to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Search for and view information about CQC-registered care
providers</li>
            <li>Integrate provider data into your own applications, products, or
reports via the API, subject to your subscription tier limits</li>
            <li>Submit genuine reviews based on real experiences with care
providers</li>
            <li>Submit enquiries to care providers through our contact
forms</li>
            <li>Claim a provider listing if you are authorised to represent that
provider</li>
            <li>Export data within the limits of your subscription tier</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Prohibited
activities</h2>
          <p>You must not:</p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.1 Data
misuse</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Scrape, crawl, or bulk-download data beyond the limits of your
subscription tier</li>
            <li>Redistribute, resell, or sublicense CareGist data as a competing
directory or data product without our prior written consent</li>
            <li>Remove or obscure CQC attribution when displaying provider data
sourced from CareGist</li>
            <li>Present CareGist data as your own original data or claim
affiliation with the Care Quality Commission</li>
            <li>Use data obtained from CareGist to send unsolicited marketing
communications to care providers (spam)</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.2 API
abuse</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Attempt to circumvent rate limits, authentication, or tier
restrictions</li>
            <li>Create multiple free accounts to avoid purchasing a paid
subscription</li>
            <li>Share API keys with third parties or embed them in publicly
accessible client-side code</li>
            <li>Use the API to conduct denial-of-service attacks, load testing,
or vulnerability scanning without our written permission</li>
            <li>Reverse-engineer, decompile, or attempt to extract source code
from the API</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.3 Harmful
content</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Submit false, misleading, or defamatory reviews about care
providers</li>
            <li>Submit fraudulent provider claims or impersonate a provider
representative</li>
            <li>Use the platform to harass, threaten, or intimidate care
providers, their staff, or residents</li>
            <li>Submit enquiries that are abusive, fraudulent, or intended to
waste a provider&apos;s time</li>
            <li>Post content that is illegal, discriminatory, or violates the
rights of others</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.4
Technical abuse</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Introduce malware, viruses, or malicious code through the API or
website</li>
            <li>Attempt to gain unauthorised access to our systems, databases,
or other users&apos; accounts</li>
            <li>Interfere with the availability or performance of the service
for other users</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. API usage
rules</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.1 Rate
limits</h3>
          <p>Each subscription tier has defined burst, daily, 7-day, and monthly
limits. These are enforced automatically. When you exceed a limit:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>The API returns HTTP 429 (Too Many Requests)</li>
            <li>Response headers indicate your remaining quota and reset
time</li>
            <li>You should implement backoff logic in your application</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.2 API key
security</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Store API keys securely (environment variables, secrets
managers) — never in source code, client-side JavaScript, or public
repositories</li>
            <li>Rotate your API key immediately if you suspect it has been
compromised (use the /api/v1/auth/rotate-key endpoint)</li>
            <li>Each API key is for use by a single organisation. Pro includes 3
named access seats, Business includes 10, and larger arrangements run through
Enterprise.</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.3
Attribution</h3>
          <p>
            When displaying CareGist data in your application, you must include
the following attribution
            in a visible location:
          </p>
          <p className="bg-parchment border border-stone rounded p-3 text-sm
mt-2">
            Data source: Care Quality Commission (CQC) via CareGist. CareGist is
not an official CQC service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Data storage
and caching</h2>
          <p>
            You may store CareGist data only as reasonably necessary for your
application&apos;s
            operation (e.g., caching search results for display). You must not:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Build or maintain a separate database containing a substantial
portion of the CareGist dataset</li>
            <li>Create local copies or mirrors of the CareGist database</li>
            <li>Store bulk data for offline use beyond your current operational
needs</li>
            <li>Retain cached data for longer than 7 days without refreshing
from the API</li>
          </ul>
          <p className="mt-2">
            Long-term storage, bulk caching, or systematic replication of the
database is prohibited
            without a commercial data licence. Bulk datasets and commercial
redistribution licences
            are available under separate agreements — contact{" "}
            <a href="mailto:sales@caregist.co.uk" className="text-clay
underline">sales@caregist.co.uk</a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Competing
services</h2>
          <p>
            You may not use CareGist data or the CareGist API to build, operate,
or improve a competing
            directory, database, or data product that substantially replicates
the CareGist service.
            This includes using CareGist data to seed, train, or populate an
alternative care provider
            directory.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Automated
data collection</h2>
          <p>
            Automated access to CareGist, including scraping, crawling, or
systematic downloading of
            data, is only permitted through the official API and within your
subscription tier limits.
            Any automated access that bypasses the API (e.g., scraping web
pages) is prohibited
            regardless of the method used.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Fair use</h2>
          <p>
            Even within published rate limits, you must not use the service in a
way that places
            excessive load on our systems or attempts to download a substantial
portion of the database.
            We reserve the right to limit or suspend accounts that we reasonably
believe are attempting
            to replicate the CareGist dataset, even if individual requests are
within tier limits.
          </p>
          <p className="mt-2">
            Examples of usage patterns that may trigger fair use review:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Systematically paginating through the entire dataset</li>
            <li>Requesting every provider by ID or slug in sequence</li>
            <li>Running the same broad query repeatedly with different
pagination offsets</li>
            <li>Sustained usage at maximum rate limits for extended periods</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Monitoring
and enforcement</h2>
          <p>We monitor API usage patterns to detect abuse. If we identify a
violation of this policy, we may:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Warn</strong> — notify you of the violation and request
corrective action</li>
            <li><strong>Throttle</strong> — temporarily reduce your rate
limits</li>
            <li><strong>Suspend</strong> — temporarily disable your API key
pending investigation</li>
            <li><strong>Terminate</strong> — permanently revoke your account and
API access</li>
          </ul>
          <p className="mt-2">
            We will provide reasonable notice before taking enforcement action,
except where immediate
            action is necessary to prevent harm to our service, other users, or
care providers.
          </p>
          <p className="mt-2">
            Unauthorised use of CareGist data may cause irreparable harm to our
business. We reserve
            the right to seek injunctive relief and damages where necessary to
protect our data,
            service, and users.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Reporting
violations</h2>
          <p>
            If you believe another user is violating this policy, or if you have
concerns about content
            on our platform, please report it to{" "}
            <a href="mailto:abuse@caregist.co.uk" className="text-clay
underline">abuse@caregist.co.uk</a>.
            We investigate all reports and respond within 5 working days.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Contact</h2>
          <p>
            Questions about this policy: <a href="mailto:legal@caregist.co.uk"
className="text-clay underline">legal@caregist.co.uk</a>
          </p>
        </section>

      </div>
    </div>
  );
}


===== FILE: api/config.py =====
"""Application configuration via environment variables."""

from __future__ import annotations

import base64
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


AWS_SECRET_ID_ENV = "AWS_SECRETS_MANAGER_SECRET_ID"
AWS_REGION_ENV = "AWS_REGION"

SECRET_ENV_NAMES = {
    "database_url": "DATABASE_URL",
    "api_master_key": "API_MASTER_KEY",
    "api_master_key_previous": "API_MASTER_KEY_PREVIOUS",
    "stripe_secret_key": "STRIPE_SECRET_KEY",
    "stripe_webhook_secret": "STRIPE_WEBHOOK_SECRET",
    "stripe_price_alerts_pro": "STRIPE_PRICE_ALERTS_PRO",
    "stripe_price_starter": "STRIPE_PRICE_STARTER",
    "stripe_price_pro": "STRIPE_PRICE_PRO",
    "stripe_price_pro_seat": "STRIPE_PRICE_PRO_SEAT",
    "stripe_price_business": "STRIPE_PRICE_BUSINESS",
    "stripe_price_enterprise": "STRIPE_PRICE_ENTERPRISE",
    "stripe_price_profile_enhanced": "STRIPE_PRICE_PROFILE_ENHANCED",
    "stripe_price_profile_premium": "STRIPE_PRICE_PROFILE_PREMIUM",
    "stripe_price_profile_sponsored": "STRIPE_PRICE_PROFILE_SPONSORED",
    "resend_api_key": "RESEND_API_KEY",
    "caregist_to_support_token": "CAREGIST_TO_SUPPORT_TOKEN",
    "support_internal_token": "SUPPORT_INTERNAL_TOKEN",
    "hermes_internal_token": "HERMES_INTERNAL_TOKEN",
    "webhook_secret_key": "WEBHOOK_SECRET_KEY",
    "redis_url": "REDIS_URL",
    "cron_secret": "CRON_SECRET",
}
SECRET_ENV_ALIASES = {
    "api_master_key": ("API_KEY",),
    "stripe_price_alerts_pro": ("STRIPE_PRICE_ALERTS_PRO_MONTHLY",),
    "stripe_price_starter": ("STRIPE_PRICE_DATA_STARTER_MONTHLY",),
    "stripe_price_pro": ("STRIPE_PRICE_DATA_PRO_MONTHLY",),
    "stripe_price_business": ("STRIPE_PRICE_DATA_BUSINESS_MONTHLY",),
    "stripe_price_profile_enhanced":
("STRIPE_PRICE_PROVIDER_ENHANCED_LISTING_MONTHLY",),
    "stripe_price_profile_premium":
("STRIPE_PRICE_PROVIDER_PRO_LISTING_MONTHLY",),
    "stripe_price_profile_sponsored":
("STRIPE_PRICE_SPONSORED_LISTING_MONTHLY",),
}
REQUIRED_PRODUCTION_SECRETS = (
    "database_url",
    "api_master_key",
    "support_internal_token",
    "stripe_secret_key",
    "stripe_webhook_secret",
    "webhook_secret_key",
    "redis_url",
)


class AwsSecretsManagerSecretLoader:
    """Load application secrets from one JSON secret in AWS Secrets Manager."""

    def __init__(self, secret_id: str, region_name: str | None = None):
        self.secret_id = secret_id
        self.region_name = region_name

    def load(self) -> dict:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised only in
incomplete deployments
            raise RuntimeError("boto3 is required to load production secrets
from AWS Secrets Manager.") from exc

        client = boto3.client("secretsmanager", region_name=self.region_name)
        response = client.get_secret_value(SecretId=self.secret_id)
        raw_secret = response.get("SecretString")
        if raw_secret is None and response.get("SecretBinary") is not None:
            raw_secret =
base64.b64decode(response["SecretBinary"]).decode("utf-8")
        if not raw_secret:
            raise RuntimeError(f"AWS secret {self.secret_id!r} is empty.")

        try:
            payload = json.loads(raw_secret)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"AWS secret {self.secret_id!r} must be a JSON
object.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"AWS secret {self.secret_id!r} must be a JSON
object.")

        return _normalize_secret_payload(payload)


def _is_production(environ: Mapping | None = None) -> bool:
    env = environ or os.environ
    return env.get("NODE_ENV", "").lower() == "production"


def redis_required_in_production(environ: Mapping | None = None) -> bool:
    """Return whether production must have shared Redis configured.

    Vercel can use the existing durable database quota path when Redis is not
    attached; its process-local limiter still protects short burst windows.
    """
    env = environ or os.environ
    return env.get("VERCEL") != "1" and not env.get("VERCEL_ENV")


def validate_cors_origins(cors_origins: str, *, production: bool) -> None:
    """Reject wildcard or malformed CORS origins when credentials are
enabled."""
    origins =
    if not origins:
        raise RuntimeError("FATAL: CORS origins must include at least one
explicit origin.")

    for origin in origins:
        parsed = urlparse(origin)
        if origin == "*" or "*" in origin:
            if production:
                raise RuntimeError("FATAL: CORS wildcard origins are not allowed
in production.")
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or
parsed.path or parsed.params or parsed.query or parsed.fragment:
            raise RuntimeError(f"FATAL: Invalid CORS origin: {origin!r}. Use
explicit scheme://host[:port] origins.")


def _lookup_secret_value(payload: Mapping, field_name: str, env_name: str) ->
Any:
    for key in (env_name, *SECRET_ENV_ALIASES.get(field_name, ()), field_name):
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _normalize_secret_payload(payload: Mapping) -> dict:
    values: dict = {}
    for field_name, env_name in SECRET_ENV_NAMES.items():
        value = _lookup_secret_value(payload, field_name, env_name)
        if value is not None:
            values = str(value)
    return values


def _load_dev_dotenv_secrets(dotenv_path: str | Path = ".env") -> dict:
    path = Path(dotenv_path)
    if not path.exists():
        return {}
    try:
        from dotenv import dotenv_values
    except ImportError:
        return {}
    return _normalize_secret_payload(dotenv_values(path))


def _load_dev_env_secrets(environ: Mapping) -> dict:
    return _normalize_secret_payload(environ)


def load_application_secrets(
    *,
    environ: Mapping | None = None,
    dotenv_path: str | Path = ".env",
    secret_loader_cls: type[AwsSecretsManagerSecretLoader] =
AwsSecretsManagerSecretLoader,
) -> dict:
    env = environ or os.environ
    is_production = _is_production(env)
    is_vercel = env.get("VERCEL") == "1"
    secret_id = env.get(AWS_SECRET_ID_ENV)

    if not secret_id and is_production and not is_vercel:
        raise RuntimeError(f"FATAL: {AWS_SECRET_ID_ENV} must be set in
production.")

    values: dict = {}
    if not is_production:
        values.update(_load_dev_dotenv_secrets(dotenv_path))
        values.update(_load_dev_env_secrets(env))
    elif is_vercel:
        # Vercel supplies production secrets directly to the function runtime.
        # Prefer the explicitly scoped production database URL when both the
        # legacy DATABASE_URL and PROD_DATABASE_URL are present.
        values.update(_load_dev_env_secrets(env))
        if env.get("PROD_DATABASE_URL"):
            values["database_url"] = env["PROD_DATABASE_URL"]
    # Vercel is the authoritative runtime now. Ignore the retired AWS secret
    # identifier if it still exists in project metadata; trying to resolve it
    # would make every serverless invocation fail before the app can start.
    if secret_id and not is_vercel:
        loader = secret_loader_cls(secret_id, env.get(AWS_REGION_ENV))
        values.update(loader.load())

    if is_production:
        required_secrets = REQUIRED_PRODUCTION_SECRETS
        if is_vercel:
            # Quotas already use the durable DB fallback when Redis is absent.
            # Redis remains recommended, but must not prevent a Vercel function
            # from starting before a managed Redis integration is attached.
            required_secrets = tuple(name for name in required_secrets if name
!= "redis_url")
        missing =
        if missing:
            missing_env_names = ", ".join(SECRET_ENV_NAMES for name in missing)
            source = "Vercel environment" if is_vercel else "AWS Secrets
Manager"
            raise RuntimeError(f"FATAL: Missing required production secrets in
{source}: {missing_env_names}")
        return {name: values.get(name, "") for name in SECRET_ENV_NAMES}

    return values


class Settings(BaseSettings):
    database_url: str =
"postgresql://caregist:caregist_dev@localhost:5432/caregist"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_master_key: str = ""
    # Optional comma-separated additional master keys, valid during a rotation
    # window so a new key can be deployed before the old one is revoked (F-18).
    api_master_key_previous: str = ""

    def master_keys(self) -> tuple:
        """All currently-valid master keys (primary + rotation overlap)."""
        keys =
        keys.extend(part.strip() for part in
self.api_master_key_previous.split(",") if part.strip())
        return tuple(key for key in keys if key)
    cors_origins: str = "http://localhost:3000"
    query_timeout_ms: int = 10000
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_alerts_pro: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_seat: str = ""
    stripe_price_business: str = ""
    stripe_price_enterprise: str = ""
    stripe_price_profile_enhanced: str = ""
    stripe_price_profile_premium: str = ""
    stripe_price_profile_sponsored: str = ""
    default_page_size: int = 20
    app_url: str = "http://localhost:3000"
    resend_api_key: str = ""
    enquiry_from_email: str = ""
    sentry_dsn: str = ""
    support_platform_url: str = ""
    caregist_to_support_token: str = ""
    support_internal_token: str = ""
    # Optional separate token for Hermes. When unset, Hermes cannot authenticate
    # as its own actor and must not share the support-platform token.
    hermes_internal_token: str = ""
    # AES-GCM key for webhook secret encryption. Must be 32 bytes,
base64-encoded.
    # If unset, webhook secrets are stored plaintext (dev/legacy mode).
    webhook_secret_key: str = ""
    # Optional Redis URL for shared burst rate limiting across workers.
    # When unset, burst limiting falls back to the process-local in-memory dict.
    redis_url: str = ""
    # Vercel Cron sends this value as an Authorization bearer token.
    cron_secret: str = ""
    # Human Gate control: provider claims remain disabled until identity,
    # authority, moderation, privacy, and operational approvals are recorded.
    provider_claims_enabled: bool = False
    # Personal-data intake and user-controlled remote media remain fail-closed
    # until the associated Human Gate privacy/moderation decisions are approved.
    enquiries_enabled: bool = False
    review_submissions_enabled: bool = False
    remote_provider_media_enabled: bool = False
    # Commercial mutations remain disabled until Human Gate 1 plus the
    # applicable finance/legal approvals are recorded. Stripe webhook intake
    # remains available so already-created state can still be reconciled.
    billing_checkout_enabled: bool = False
    outbound_communications_enabled: bool = False
    monitoring_activation_enabled: bool = False
    outbound_delivery_enabled: bool = False
    directory_export_delivery_enabled: bool = False
    review_publication_enabled: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra":
"ignore"}

    def validate_production(self) -> None:
        validate_cors_origins(self.cors_origins, production="localhost" not in
self.database_url)

        if "pytest" in sys.modules:
            return

        if not self.api_master_key:
            raise RuntimeError("FATAL: API_MASTER_KEY is required.")
        if not self.support_internal_token:
            raise RuntimeError("FATAL: SUPPORT_INTERNAL_TOKEN is required.")

        is_localhost = self.database_url ==
"postgresql://caregist:caregist_dev@localhost:5432/caregist"
        is_production_db = "localhost" not in self.database_url
        if is_production_db:
            if not self.webhook_secret_key:
                raise RuntimeError("FATAL: WEBHOOK_SECRET_KEY is required in
production.")
            if not self.redis_url and redis_required_in_production():
                raise RuntimeError("FATAL: REDIS_URL is required in
production.")

        # Stripe environment guard: reject live keys in dev/test
        if self.stripe_secret_key.startswith("sk_live_") and is_localhost:
            raise RuntimeError(
                "FATAL: Live Stripe secret key (sk_live_) detected in local
development environment. "
                "Use test credentials (sk_test_) for development. "
                "Live keys are only for production deployments."
            )


settings = Settings(**load_application_secrets())
settings.validate_production()

# --- Tier definitions (single source of truth) ---

# Tier limits — staircase designed around job-to-be-done, not just usage caps.
# Free is intentionally constrained to evaluation. Paid tiers are built around
the
# first solo workflow, small-team production use, and higher-volume operational
integration.
TIERS = {
    "free": {
        "rate": 2,
        "rate_window_seconds": 1,
        "daily": 20,
        "rolling_7d": 60,
        "monthly": 300,
        "page_size": 5,
        "fields": "basic",
        "nearby": False,
        "export": 0,
        "exports_per_day": 0,
        "compare": 0,
        "webhooks": False,
        "monitors": 1,
        "feed_rows": 10,
        "saved_filters": 0,
        "feed_digests": 0,
        "feed_api": False,
        "included_users": 1,
        "base_price_gbp": 0,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "next_tier": "starter",
    },
    "alerts-pro": {
        "rate": 5,
        "rate_window_seconds": 1,
        "daily": 200,
        "rolling_7d": 1400,
        "monthly": 5000,
        "page_size": 10,
        "fields": "standard",
        "nearby": False,
        "export": 0,
        "exports_per_day": 0,
        "compare": 3,
        "webhooks": False,
        "monitors": 50,
        "feed_rows": 0,
        "saved_filters": 0,
        "feed_digests": 0,
        "feed_api": False,
        "included_users": 1,
        "base_price_gbp": 49,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "next_tier": "starter",
    },
    "starter": {
        "rate": 10,
        "rate_window_seconds": 1,
        "daily": 500,
        "rolling_7d": 3500,
        "monthly": 10000,
        "page_size": 20,
        "fields": "standard",
        "nearby": True,
        "export": 500,
        "exports_per_day": 10,
        "compare": 3,
        "webhooks": False,
        "monitors": 15,
        "feed_rows": 25,
        "saved_filters": 3,
        "feed_digests": 1,
        "feed_api": True,
        "included_users": 1,
        "base_price_gbp": 99,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "next_tier": "pro",
    },
    "pro": {
        "rate": 25,
        "rate_window_seconds": 1,
        "daily": 2000,
        "rolling_7d": 14000,
        "monthly": 50000,
        "page_size": 50,
        "fields": "standard",
        "nearby": True,
        "export": 5000,
        "exports_per_day": 50,
        "compare": 5,
        "webhooks": False,
        "monitors": 100,
        "feed_rows": 50,
        "saved_filters": 20,
        "feed_digests": 10,
        "feed_api": True,
        "included_users": 3,
        "base_price_gbp": 199,
        "seat_price_gbp": 15,
        "extra_seat_min_tier": "pro",
        "next_tier": "business",
    },
    "business": {
        "rate": 60,
        "rate_window_seconds": 1,
        "daily": 10000,
        "rolling_7d": 70000,
        "monthly": 250000,
        "page_size": 100,
        "fields": "full",
        "nearby": True,
        "export": 10000,
        "exports_per_day": 100,
        "compare": 10,
        "webhooks": True,
        "monitors": 500,
        "feed_rows": 100,
        "saved_filters": 100,
        "feed_digests": 100,
        "feed_api": True,
        "included_users": 10,
        "base_price_gbp": 499,
        "seat_price_gbp": 15,
        "extra_seat_min_tier": "business",
        "next_tier": "enterprise",
    },
    "enterprise": {
        "rate": 200,
        "rate_window_seconds": 1,
        "daily": 50000,
        "rolling_7d": 350000,
        "monthly": 1500000,
        "page_size": 100,
        "fields": "full",
        "nearby": True,
        "export": 50000,
        "exports_per_day": 500,
        "compare": 20,
        "webhooks": True,
        "monitors": 5000,
        "feed_rows": 250,
        "saved_filters": 500,
        "feed_digests": 500,
        "feed_api": True,
        "included_users": 10,
        "base_price_gbp": 0,
        "seat_price_gbp": 15,
        "extra_seat_min_tier": "business",
        "next_tier": None,
    },
    "admin": {
        "rate": 99999,
        "rate_window_seconds": 1,
        "daily": 9999999,
        "rolling_7d": 99999999,
        "monthly": 99999999,
        "page_size": 100,
        "fields": "full",
        "nearby": True,
        "export": 99999,
        "exports_per_day": 99999,
        "compare": 99,
        "webhooks": True,
        "monitors": 99999,
        "feed_rows": 1000,
        "saved_filters": 99999,
        "feed_digests": 99999,
        "feed_api": True,
        "included_users": 99999,
        "base_price_gbp": 0,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": "pro",
        "next_tier": None,
    },
}

# Fields included in the free-tier basic CSV export
# Deliberately richer than CQC's own CSV (which omits ratings entirely)
BASIC_CSV_FIELDS = [
    "name", "town", "county", "postcode", "region", "local_authority",
    "phone", "website", "overall_rating", "type", "service_types",
    "specialisms", "number_of_beds", "data_completeness_score",
"data_completeness_tier",
    "last_inspection_date", "inspection_report_url",
]

BASIC_FIELDS = [
    "id", "name", "slug", "type", "status", "town", "county", "postcode",
    "region", "local_authority", "overall_rating", "service_types",
    "specialisms", "number_of_beds", "data_completeness_score",
"data_completeness_tier",
    "phone", "website", "last_inspection_date", "inspection_report_url",
    "inspection_summary", "profile_description", "profile_photos",
    "virtual_tour_url", "inspection_response", "profile_tier",
    "logo_url", "funding_types", "fee_guidance", "min_visit_duration",
    "contract_types", "age_ranges",
]

STANDARD_FIELDS = BASIC_FIELDS + [
    "email", "latitude", "longitude",
    "regulated_activities", "ownership_type",
    "rating_safe", "rating_effective", "rating_caring",
    "rating_responsive", "rating_well_led",
    "is_claimed", "review_count", "avg_review_rating",
]

FULL_FIELDS = STANDARD_FIELDS + [
    "provider_id", "registration_date", "geocode_source",
    "data_source", "data_attribution", "created_at", "updated_at",
]

FIELD_SETS = {
    "basic": set(BASIC_FIELDS),
    "standard": set(STANDARD_FIELDS),
    "full": set(FULL_FIELDS),
}

TIER_RANK = {
    "free": 0,
    "alerts-pro": 1,
    "starter": 2,
    "pro": 3,
    "business": 4,
    "enterprise": 5,
    "admin": 6,
}


def get_tier_config(tier: str) -> dict:
    """Get config for a tier, defaulting to free."""
    normalized = (tier or "free").lower()
    if normalized in TIERS:
        return TIERS
    if normalized.startswith("enterprise"):
        return TIERS["enterprise"]
    return TIERS["free"]


def get_tier_price_gbp(tier: str) -> int:
    return int(get_tier_config(tier).get("base_price_gbp", 0))


def get_included_user_count(tier: str) -> int:
    return int(get_tier_config(tier).get("included_users", 1))


def get_seat_price_gbp(tier: str) -> int:
    return int(get_tier_config(tier).get("seat_price_gbp", 0))


def get_next_tier(tier: str) -> str | None:
    return get_tier_config(tier).get("next_tier")


def get_tier_rank(tier: str) -> int:
    normalized = (tier or "free").lower()
    if normalized.startswith("enterprise"):
        normalized = "enterprise"
    return int(TIER_RANK.get(normalized, 0))


def max_tier(*tiers: str | None) -> str:
    candidates =
    if not candidates:
        return "free"
    return max(candidates, key=get_tier_rank)


def allows_extra_seats(tier: str) -> bool:
    return get_seat_price_gbp(tier) > 0


def get_max_users(tier: str, extra_seats: int = 0) -> int:
    base = get_included_user_count(tier)
    return base + max(0, extra_seats) if allows_extra_seats(tier) else base


def get_subscription_entitlements(tier: str, extra_seats: int = 0) -> dict:
    config = get_tier_config(tier)
    return {
        "tier": tier,
        "included_users": get_included_user_count(tier),
        "extra_seats": max(0, extra_seats),
        "max_users": get_max_users(tier, extra_seats),
        "seat_price_gbp": get_seat_price_gbp(tier),
        "allows_extra_seats": allows_extra_seats(tier),
        "next_tier": config.get("next_tier"),
    }


def get_allowed_fields(tier: str) -> set:
    """Get the set of fields allowed for a tier."""
    config = get_tier_config(tier)
    return FIELD_SETS.get(config["fields"], FIELD_SETS["basic"])


def filter_fields(record: dict, tier: str) -> dict:
    """Strip fields not allowed by the tier. Hidden fields become None."""
    allowed = get_allowed_fields(tier)
    return {k: (v if k in allowed else None) for k, v in record.items()}


===== FILE: .env.example =====
# Directory MVP (Next.js frontend + Vercel Postgres)
POSTGRES_URL=postgresql://user:password@host:5432/database?sslmode=require
STRIPE_PAYMENT_LINK_URL=https://buy.stripe.com/your-payment-link
LEAD_NOTIFY_EMAIL=
DIRECTORY_TOKEN_SECRET=replace-with-at-least-32-random-characters
FORWARDED_ALLOW_IPS=127.0.0.1
TRUSTED_PROXY_CIDRS=127.0.0.0/8,::1/128
APP_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# CQC API subscription key — get one at
https://anypoint.mulesoft.com/exchange/portals/care-quality-commission-5/
CQC_API_KEY=your_api_key_here

# PostgreSQL connection
DATABASE_URL=postgresql://caregist:caregist_dev@localhost:5432/caregist
# Release migrations must use target-specific URLs. Do not point these at the
same database.
STAGING_DATABASE_URL=postgresql://user:password@staging-host:5432/caregist?sslmo
de=require
PROD_DATABASE_URL=postgresql://user:password@prod-host:5432/caregist?sslmode=req
uire

# API settings
API_HOST=0.0.0.0
API_PORT=8000
API_MASTER_KEY=change_me_in_production
# Optional: comma-separated previous master key(s), valid during a rotation
# window so a new key can be deployed before the old one is revoked.
API_MASTER_KEY_PREVIOUS=
APP_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
QUERY_TIMEOUT_MS=10000
DEFAULT_PAGE_SIZE=20

# Frontend server/client API wiring
API_URL=http://localhost:8000
API_KEY=dev_key_change_me
NEXT_PUBLIC_API_URL=http://localhost:8000
# Never set NEXT_PUBLIC_API_KEY. It would expose a privileged backend key to the
browser bundle.
SUPPORT_PLATFORM_URL=http://localhost:3002
CAREGIST_TO_SUPPORT_TOKEN=replace_me
SUPPORT_INTERNAL_TOKEN=replace_me
# Optional separate token for Hermes brokered control-plane access.
# Keep unset until Hermes is explicitly wired; never reuse
SUPPORT_INTERNAL_TOKEN.
HERMES_INTERNAL_TOKEN=
NEXT_PUBLIC_SUPPORT_PLATFORM_URL=http://localhost:3002
NEXT_PUBLIC_SUPPORT_PLATFORM_TOKEN=replace_me

# Stripe (get keys from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
# B2B data intelligence tiers
STRIPE_PRICE_ALERTS_PRO=price_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_PRO_SEAT=price_...
STRIPE_PRICE_BUSINESS=price_...
# Provider listing tiers (supply-side — care providers paying to enhance
profiles)
STRIPE_PRICE_PROFILE_ENHANCED=price_...
STRIPE_PRICE_PROFILE_PREMIUM=price_...
STRIPE_PRICE_PROFILE_SPONSORED=price_...

# Resend (transactional email — https://resend.com)
RESEND_API_KEY=re_...
ENQUIRY_FROM_EMAIL=noreply@caregist.co.uk
MONITOR_ALERT_FAILURE_EMAIL=ops@caregist.co.uk

# Sentry (error tracking — https://sentry.io)
SENTRY_DSN=https://...@sentry.io/...
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...

# Webhook secret encryption (AES-256-GCM, 32 bytes base64-encoded).
# Generate with: python -c "import base64, os;
print(base64.b64encode(os.urandom(32)).decode())"
# If unset, webhook signing secrets are stored plaintext (dev/legacy). Required
for production.
WEBHOOK_SECRET_KEY=

# Redis URL for shared burst/quota rate limiting across API workers.
# Example: redis://localhost:6379/0 or rediss://:password@host:6380/0
# If unset, rate limits fall back to per-process in-memory state — do not run
production without Redis.
REDIS_URL=
# Human-gated feature controls (claims must remain false until approved)
PROVIDER_CLAIMS_ENABLED=false
ENQUIRIES_ENABLED=false
REVIEW_SUBMISSIONS_ENABLED=false
REVIEW_PUBLICATION_ENABLED=false
REMOTE_PROVIDER_MEDIA_ENABLED=false
BILLING_CHECKOUT_ENABLED=false
OUTBOUND_COMMUNICATIONS_ENABLED=false
MONITORING_ACTIVATION_ENABLED=false
OUTBOUND_DELIVERY_ENABLED=false
# Next.js routes that collect lead data or deliver directory exports.
DIRECTORY_LEAD_INTAKE_ENABLED=false
DIRECTORY_EXPORT_DELIVERY_ENABLED=false

Initializing agent...
────────────────────────────────────────

⚠️ No response from provider for 1472s (model: deepseek-v4-pro, context: ~43,972 tokens). Reconnecting...
⚠️ deepseek stream drop (RemoteProtocolError) after 1536.1s — reconnecting, retry 2/3
⚠️  API call failed (attempt 1/3): APIConnectionError
   🔌 Provider: deepseek  Model: deepseek-v4-pro
   🌐 Endpoint: https://api.deepseek.com/v1
   📝 Error: Connection error.
   ⏱️  Elapsed: 1536.13s  Context: 2 msgs, ~25,739 tokens
⏳ Retrying in 2.7s (attempt 1/3)...
⚠️  API call failed (attempt 2/3): APIConnectionError
   🔌 Provider: deepseek  Model: deepseek-v4-pro
   🌐 Endpoint: https://api.deepseek.com/v1
   📝 Error: Connection error.
   ⏱️  Elapsed: 1539.03s  Context: 2 msgs, ~25,739 tokens
⚠️ Provider unreachable — switching to fallback provider...
🔄 Primary model failed — switching to fallback: kimi-k3 via kimi-coding
⚠️  API call failed (attempt 1/3): APIConnectionError
   🔌 Provider: kimi-coding  Model: kimi-k3
   🌐 Endpoint: https://api.moonshot.ai/v1/
   📝 Error: Connection error.
   ⏱️  Elapsed: 1539.05s  Context: 2 msgs, ~25,739 tokens
⏳ Retrying in 2.5s (attempt 1/3)...
⚠️  API call failed (attempt 2/3): APIConnectionError
   🔌 Provider: kimi-coding  Model: kimi-k3
   🌐 Endpoint: https://api.moonshot.ai/v1/
   📝 Error: Connection error.
   ⏱️  Elapsed: 2360.19s  Context: 2 msgs, ~25,739 tokens
⏳ Retrying in 5.0s (attempt 2/3)...
⚠️  API call failed (attempt 3/3): APIConnectionError
   🔌 Provider: kimi-coding  Model: kimi-k3
   🌐 Endpoint: https://api.moonshot.ai/v1/
   📝 Error: Connection error.
   ⏱️  Elapsed: 2365.34s  Context: 2 msgs, ~25,739 tokens
❌ API failed after 3 retries — Connection error.
   💀 Final error: Connection error.
 ─  ⚕ Hermes  ─────────────────────────────────────────────────────────────────

     API call failed after 3 retries: Connection error.

 ──────────────────────────────────────────────────────────────────────────────

⚠ Iteration budget reached (1/1) — response may be incomplete

Resume this session with:
  hermes --resume 20260730_125055_4ceadb -p ai-company-governed

Session:        20260730_125055_4ceadb
Duration:       39m 29s
Messages:       1 (1 user, 0 tool calls)
