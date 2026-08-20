# Next actions

Updated: 2026-08-20T11:05Z

**Single next bounded action:** Review local live-lineage candidate `codex/last10-integration-20260820` at `738de4ae279533192d9ed35a3223d5e7b32b545f`, then authorise only a push/PR and require CI to reproduce the frozen validation. The candidate is a direct descendant of `origin/main` and is based exactly on reviewed live SHA `f7a9dd19fd340587e7b6ac2080c5116100066f27`; it reconciles both lines without the stale-main website regression. Code-local DOD is 10/10, but production evidence is 0/9. The cleaned governance branch is not a release candidate. Do not enable checkout, Radar delivery, collectors, claims, leads, exports, or notifications.

Then:

1. Henry reviews and authorises push/PR of the unified live-lineage candidate; PR CI must pass before merge.
2. Configure the promoted frontend/backend SHA variables deliberately before the new production smoke reaches default main. Keep watchdog notifications false until both delivery secrets exist.
3. After merge, observe one scheduled signal poll at the exact Actions head SHA. Separately authorise the bounded eight-shard/four-worker reconciliation; permit at most its single manual resume wave.
4. Grok re-tests the deployed homepage count, service 404, pricing/checkout fail-closed state, entitlement, freshness, and release identities step by step.
5. DeepSeek challenges the frozen packet. Synthetic login/entitlement/CallSid still needs Henry yes/no.

Do not enable checkout. Do not create a live charge. Do not deploy the governance branch as a release candidate.
