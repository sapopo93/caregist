# Territory Opportunity Brief deployment handoff

## Objective

Publish a customer-facing, factual £795 Territory Opportunity Brief offer that a remote VA can share, and prevent the currently closed roadmap tiers from being purchased through a pricing card.

## Files changed

- `frontend/app/territory-opportunity-brief/page.tsx` — public offer at `/territory-opportunity-brief`: buyer, £795 price, no-VAT wording, four deliverables, scope check, three-working-day target, dated sample context and product limits.
- `frontend/components/PricingCTA.tsx` — early checkout guard for Radar Regional, Radar National, Intelligence Feed Pilot and Embedded Enterprise.
- `frontend/lib/pricing-provider-cta.test.ts` — regression check that the guard appears before the checkout handler.

## Checks performed and results

- `npm test` in `frontend`: PASS, 162 tests, 0 failures, before the clean worktree ran out of local disk space during a package install.
- `node --experimental-strip-types --test lib/pricing-provider-cta.test.ts`: PASS, 6 tests, 0 failures.
- `git diff --check`: PASS.
- Vercel production deployment `dpl_J3MbdsX7pFbEqgjGjXuyeZPMV2Jx`: READY.
- Public buyer view: PASS at `https://www.caregist.co.uk/territory-opportunity-brief`. The live response includes £795, “No VAT is charged”, the scope action and the corrected cream hero heading style.
- Live pricing response: PASS for the UI guard. It includes “Paid checkout unavailable” and “This product is not currently available for purchase.”
- Release identity: `https://www.caregist.co.uk/api/v1/version` reports `ee72dce41bd906f4ddee7d0e12702bc7cb1746e8`, matching `origin/main`.

## Unresolved issues affecting selling today

1. The UI guard blocks pricing-card checkout only. It does not prove that direct backend checkout routes or existing Stripe prices cannot be used. The live £795 Stripe Payment Link remains a scope-first, manually issued payment step.
2. The £495 Market Movement Report remains unsupported for sale. There is no verified current edition or verified closure-event series. The £150 Radar pilot remains source-readiness gated.

## Exact next action

Use `2026-09-09-va-territory-brief-sales-workflow.md` for every £795 sale. Confirm written scope and the source-path check before issuing the existing payment link.

## Source references

- Founder launch decision: `.hermes/profiles/ai-company-governed/company-os/chief-of-staff/decisions/2026-09-07-caregist-launch-one-off-products.md`
- Existing terms: `frontend/app/terms/page.tsx`
- Published offer: `frontend/app/territory-opportunity-brief/page.tsx`
- Checkout gate: `frontend/components/PricingCTA.tsx`
