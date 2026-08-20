# Current verdict

- Updated: 2026-08-20 11:05 UTC
- Quality: **UNPROVEN / NOT CUSTOMER-READY FOR PAID RELEASE**
- Decision: **HOLD**
- Cash from CareGist: **unproven this cycle** (no charge; checkout fail-closed)

## What is true

- Live site: https://www.caregist.co.uk — SHA `f7a9dd19fd340587e7b6ac2080c5116100066f27`
- This branch is based on `fba66d7`, an **ancestor** of live; its only retained local delta is repository governance.
- `origin/main` `051cac1` is **not** what production runs (live is 25 commits ahead of main)
- The previously dirty product tree was triaged and cleaned. Unsafe lead-engine, CRM-help, and health prototypes were removed; already-reviewed directory changes remain on their existing live-lineage commits.
- All registered, present worktrees were checked and cleaned. Stale temporary registrations are safe to prune.
- A separate clean live-lineage candidate exists at `738de4ae279533192d9ed35a3223d5e7b32b545f`; it has not been pushed, merged, or deployed.
- Code-local DOD is **10/10** across the frozen critical lanes. Production/external DOD is **0/9** because no PR, candidate CI, merge, deployment, poll/reconciliation proof, reliability window, or independent deployed-journey approval has occurred.
- Frozen candidate validation remains as previously recorded: Python 764 passed/1 skipped with isolated PostgreSQL; frontend clean install and 162 tests; Next Turbopack production build/typecheck; production HTTP 2 passed; dependency audits, Ruff/compile/YAML/diff checks passed.
- Public prices: Radar Regional £299/mo, National £799/mo, Feed from £6,000/yr, Enterprise quote-only — Stripe live objects match amounts
- Paid CTAs are **disabled** (`Paid checkout unavailable`); `commercialReadiness.checkoutReady=false`
- Directory stranger path largely works (RI 2,350; SO15=98). CQC source still incomplete; health **degraded**
- CareOps (`caregistops.co.uk`) and `api.caregist.co.uk` time out on `13.49.189.77`

## What this loop is for

Close remaining honesty, source, identity, and evidence gaps. It is not permission to take payment or deploy this tree.
