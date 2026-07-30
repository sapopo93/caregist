# Decision log

| Date | Decision | Reason / consequence |
|---|---|---|
| 2026-07-30 | Treat `quality_score` solely as legacy completeness terminology | Prevent care-quality inference and ranking misuse |
| 2026-07-30 | Reconcile locations from CQC's current official directory, then verify changed details | Removed changes endpoint cannot be authoritative; partial mutations abort |
| 2026-07-30 | Publish source and ingestion watermarks separately | A successful ingestion cannot make an old source publication fresh |
| 2026-07-30 | Use location/provider/group as separate metrics | Eliminates 55,818/56,742/56,743 denominator ambiguity |
| 2026-07-30 | Keep production import unexecuted | No production mutation or additional spend authority was given |
| 2026-07-30 | Keep checkout, intake, export delivery, remote media and claims default-off | Implementation/testing does not imply activation approval |
| 2026-07-30 | Retain Stripe webhook intake for reconciliation | Disabling new checkout must not corrupt already-existing payment state |
| 2026-07-30 | Store claim evidence fingerprints, not raw proof text/documents | Minimise identity/authority data and make re-verification explicit |
| 2026-07-30 | Replace overconfident terms/privacy assertions with controlled status pages | Entity, processor, transfer, VAT and lawful-basis facts are unverified |
| 2026-07-30 | Treat VantageData as secondary market evidence only | A competitor's conduct or “GDPR compliant” label is not CareGist legal clearance |
| 2026-07-30 | Make three proof briefs internal and non-delivering | Satisfies Gate preparation without outreach, publication, billing or exports |
| 2026-07-30 | Withdraw the stale H-Kay strike-off/overdue-filing finding | Live Companies House overview and filing history show H-Kay active, current filings, and strike-off discontinued on 28 February 2026; corporate status does not establish CareGist operator/controller authority |
