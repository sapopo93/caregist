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
| 2026-08-01 | Name H-Kay Limited (10417923) as CareGist operator, contracting party and data controller | Founder decision at Human Gate. Resolves the "competing entity reference" and aligns the terms, privacy notice and the pre-existing acceptable-use page, which already named H-Kay. Registered office verified at Companies House: C/O Bilberry Accountants Ltd, Castle Court, 41 London Road, Reigate, RH2 9RJ |
| 2026-08-01 | Replace controlled status pages with operative Terms of Service v1.0 and Privacy Notice | Founder instruction to draft and publish. **These were drafted without qualified legal review** — see the unreviewed-items list in `legal-blocker-register.md`. Publishing was an accepted risk, not a cleared blocker |
| 2026-08-01 | State prices exclusive of VAT, with VAT added where applicable, rather than asserting a VAT position | VAT registration is an entity-level fact about H-Kay Limited, which has traded since 2016 across IT consultancy and cleaning activities. CareGist's own £0 turnover does not establish H-Kay's VAT status; the wording is correct whether or not H-Kay is registered |
| 2026-08-01 | Enable checkout and monitoring activation | Follows from the entity decision and operative terms. Stripe was already fully configured (secret key, webhook secret, nine price IDs); the flags were the only thing preventing any customer from paying |
