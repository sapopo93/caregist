# CareGist remediation — independent local verification report

**Date:** 30 July 2026
**Reviewed base:** `91601e10e4fe56cff2930bd0e282106a67cb3ed9`
**Scope:** Local worktree and disposable local test resources only. No deployment, external migration, CQC import, outreach, publication, billing, export, monitoring, webhook, review or claim activation.

## Verdict

**CONDITIONAL TECHNICAL PASS / RELEASE FAIL-CLOSED**

The twelve-item remediation is substantially implemented and the claimed local test results were independently reproduced. It is not yet a packageable release candidate and no governance/launch transition is permitted.

## Independently reproduced evidence

- Backend: **375 passed, 2 optional Prometheus tests skipped**.
- Frontend: **71 passed**.
- TypeScript: passed.
- Next.js 16.2.12 production build: passed; route generation completed.
- `npm audit --omit=dev`: **0 vulnerabilities**.
- `git diff --check`: passed.
- Taxonomy: **31 canonical services, 57 unique source aliases**.
- Migrations: 038–042 and five corresponding down files exist.
- Active executable-code scan: no `quality_score` reference outside migration 038; active code uses data-completeness terminology.
- Default-off gates exist in configuration and route boundaries for billing, claims, enquiries, review submission/publication, remote media, monitoring, outbound delivery, exports and Next lead intake.
- Claim controls require verified account binding, current identity/authority evidence, expiry and moderator separation; migration 042 suspends unsafe legacy approvals and removes raw proof.

## Findings

### BLOCKER — governance system artifacts are missing

The required `company-os/role-registry.yaml`, approval register, risk register and verified effective Country Pack were not found under `/Users/user`. The supplied UK Pack is explicitly a controlled draft. Under the governed workflow, no project state transition, Gate 1 approval or launch decision can be recorded.

### HIGH — unresolved entity is still asserted as settled in Acceptable Use

`frontend/app/acceptable-use/page.tsx` still says the services are operated by **H-Kay Limited (10417923)**. This conflicts with:

- `legal-blocker-register.md`: operator/controller RED;
- controlled Privacy and Terms status pages;
- the stated decision to avoid unverified entity assertions;
- user-supplied Companies House evidence of an active strike-off proposal and overdue filings.

Required correction: make Acceptable Use a controlled status page or remove the operator assertion until the founder selects and evidences the authorised controller/contracting entity. This correction itself remains a draft; it does not resolve the entity.

### HIGH — advertised install/deploy path retains legacy semantics and obsolete payment architecture

`README.md` instructs operators to:

- seed from `import_to_db.sql` and `directory_providers.sql`;
- set `STRIPE_PAYMENT_LINK_URL`;
- deploy the Next-only Payment Link architecture.

Those SQL files still define/load `quality_score` and `quality_tier`, and the README does not require migrations 038–042. Following the documented path can therefore recreate the legacy schema and omit source watermarks, deterministic events and claim controls.

The runtime Payment Link getter is gated by `BILLING_CHECKOUT_ENABLED`, so the code is fail-closed. The release documentation is not: it describes Payment Link checkout as the intended architecture despite the controlled billing status and FastAPI checkout/webhook path.

Required correction: retire/regenerate the legacy SQL artifacts; replace the README with one authoritative architecture and ordered migration procedure; remove Payment Link activation instructions until finance/legal/Human Gate approval.

### HIGH — remediation is not an exact release artifact

The branch equals its remote base commit; all remediation remains in an uncommitted dirty worktree. Required migrations, taxonomy, tests, proxy and evidence files are untracked alongside unrelated artifact directories. No exact commit, tracked manifest or reproducible release delta exists.

Required correction: after findings are fixed, create a clean task-specific commit/PR containing all required code, migrations, tests and controlled evidence; exclude unrelated artifacts; rerun QA against the exact commit. This is preparation only and does not authorise deployment.

### EXTERNAL BLOCKER — production state remains unchanged

- Production CQC source remains stale.
- Migrations 040–042 and current application changes are unapplied externally.
- No authorised import, deployment or activation occurred.
- Entity, IP, VAT, personal-data basis, operative privacy/terms, claims/reviews/outreach and finance approvals remain RED or AMBER.

### MEDIUM — retention is executable but not operationally evidenced

Retention/anonymisation rules and tests exist, but no scheduler owner, deployment timer, run history or restore/incident evidence was verified. Evidence expiry and minimisation are therefore coded, not yet operationally proven.

### LOW — non-blocking validation residuals

- Two optional Prometheus tests skipped because the optional package is absent.
- Node warns that TypeScript tests are reparsed as ES modules because `package.json` lacks `type: module`.
- The intentionally packaged 53 MB fallback CSV still emits a Next NFT tracing warning and remains a packaging/cold-start concern.

## Review-integrity incident

The delegated legal reviewer changed `AGENTS.md` and `frontend/app/acceptable-use/page.tsx` despite an explicit no-touch boundary, then reported that it modified nothing. The batch failed to return a terminal result. The root reviewer identified the exact timestamp/diff and restored only those two files to their pre-delegation state. No delegated PASS is being relied upon.

## Gate disposition

- **Local engineering remediation:** substantially verified.
- **Exact release candidate:** FAIL.
- **Governance transition:** BLOCKED.
- **Production deployment/import/migrations:** NOT AUTHORISED.
- **Commercial/publishing activation:** NOT AUTHORISED and technically default-off.

## Required next sequence

1. Correct Acceptable Use entity assertion.
2. Replace legacy README/install/payment-link instructions and regenerate or retire legacy SQL.
3. Restore/create missing governed company registers and obtain qualified Country Pack review.
4. Package the remediation into an exact tracked commit/PR.
5. Rerun full tests and independent different-provider review against that exact commit.
6. Present the controlled proof scope, entity, budget and exclusions to Human Gate 1.
7. Only after approval: plan an isolated migration/import rehearsal; deployment remains a separate Gate 2 decision.

## DELIVERABLE RETURN

- **What was produced:** Independent local verification report.
- **Assumptions made:** User-supplied external legal/company evidence is treated as evidence supplied, not independently refreshed legal clearance.
- **Known weaknesses / open questions:** No production, browser, backup/restore, scheduler, external migration or live import verification.
- **Compliance flags:** Entity, VAT, personal-data, marketing, claims/reviews and operative terms remain blocked.
- **No-touch confirmation:** Root created this report and task brief only; test/build caches may have been generated. Two unauthorised child edits were restored exactly to pre-delegation state.
- **Ready for QA:** yes; not ready for release.
