# Top blockers

Updated: 2026-08-20

| # | Blocker | Why it matters | Owner |
|---|---|---|---|
| 1 | Unified live-lineage recovery candidate is local (`738de4ae279533192d9ed35a3223d5e7b32b545f`); no reviewed PR/merge, observed clean poll, or completed authoritative reconciliation yet | Paid “verified source” is still unproven | Engineering collectors + Henry gate |
| 2 | `checkoutReady=false` (correct) while Radar prices remain public | Must stay fail-closed | Henry flag decision |
| 3 | This governance branch ≠ live SHA | It is clean, but it is still not a release candidate | Henry / Hermes |
| 4 | Production SHA ≠ `origin/main`; unified candidate is correctly based on live but default-main integration is still pending | Scheduled workflow and web promotion identities remain separate | Henry |
| 5 | No synthetic login / entitlement / CallSid | Historical green-lie class | Henry + Grok |
| 6 | Exact homepage rating and real service 404 fixes are in the unified candidate, but not deployed/retested | Current live homepage count is misleading and unknown service paths still return HTTP 200 | Henry deploy gate + Grok |
| 7 | CareOps + api.caregist.co.uk timeout | Residual webhook / ops risk | Ops (read-only) |
| 8 | No DeepSeek challenge of this 20 Aug packet | Cannot reach PROVEN | Hermes → DeepSeek |
| 9 | £150 payable-lead path has zero accept/invoice | No cash this cycle | Henry + VA |
| 10 | Organisation entitlement sync and unconditional Radar delivery checkout gate are in the unified candidate, but not merged or replayed in a deployed buyer journey | Checkout return cannot yet be certified end to end | Engineering + Grok |
