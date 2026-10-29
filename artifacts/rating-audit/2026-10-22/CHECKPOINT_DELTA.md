# CURRENT_VERDICT.md

## 2026-10-22 rating website audit — PARTIAL, no gate approval

Live frontend SHA c50d07e (PR #122) observed read-only. Frozen 30-ID stratified sample: 20 file-backed, all five conflicts, five stored-blank/file-absent. Search badges/positive filters follow the deployed rule 30/30; file labels 20/20. Website: 18 current numerical matches, five numerical mismatches, two current/inherited-context exceptions, five without a numerical location overall. Zero inaccessible pages. This is not national accuracy evidence. Four conflicts prove live API publication dates can predate file/website evidence; one mismatch is a post-snapshot website update. Deployed Brief still reads API NDJSON, omitting file fallback from its rating fields, narrative, evidence appendix and exports; public coverage uses reconciled directory predicates. Local uncommitted Postgres source work is not deployed. Independent review pending; producer audit is not approval.

Evidence: [audit report](../artifacts/rating-audit/2026-10-22/REPORT.md), per-ID audit.csv/results.json, raw API/HTML/ODS and MANIFEST.sha256. Exact exceptions: 1-125730630, 1-152721284, 1-22160036426, 1-390976877, 1-552527797; contextual: 1-16491295796, 1-19886383752. Query snapshot: 57,196 active, 32,060 active file-rated, 101 inactive file-rated. Source cutoff labelled 1 Oct is not independently established. No production data, gate, code, merge or deploy change. This dated delta supersedes older rating-audit claims only. Historical DeepSeek references are obsolete: current AGENTS.md prohibits that provider.


# TOP_BLOCKERS.md

## 2026-10-22 rating audit blockers — current bounded evidence

1. Brief rating contents have no file-rating input at deployed c50d07e. The exact deployed reader returns no rating on all 20 saved file-backed API fixtures even when file fields are present alongside the payload.
2. Four API/file conflicts select old API ratings despite newer website/file evidence: 1-152721284, 1-22160036426, 1-390976877, 1-552527797. Wholesale API-first precedence is not evidence of current accuracy.
3. Current/inherited status unresolved for 1-16491295796 and 1-19886383752; 1-125730630 has a newer 13 Oct website rating. Do not silently choose a source or claim a verified current inspection.
4. File cutoff/provenance label needs verification: label says 1 Oct; ODS metadata and CQC download label say 2 Oct (not proof of data cutoff). Stripe Projects' named production-db lacks the rating column while existing .env database matches all 30 public samples; hosting target mapping is not independently established.
5. Independent approved-provider challenge and complete customer Brief acceptance remain pending. All named commercial gates remain unchanged. DeepSeek is prohibited under current AGENTS.md.

[Evidence and denominators](../artifacts/rating-audit/2026-10-22/REPORT.md). Do not repeat the closed PR #122 label fix.


# NEXT_ACTIONS.md

## 2026-10-22 single next bounded fix — proposal, not implementation

Prepare a provenance-aware resolved-current-rating input contract for the Territory Brief, consistently carried through current-state tables, narrative, evidence appendix, PDF/CSV/JSON and rating-based scope decisions. Preserve API/file values, publication dates, edition/hash and current/inherited/unresolved status. Do not duplicate unconditional API-first precedence or invent rating-change events from a snapshot. Use the frozen 20 file-backed, five conflict and five unrated fixtures, plus the observed post-snapshot/current-provider cases, as acceptance evidence. No implementation was performed by this audit.

First challenge the [frozen evidence packet](../artifacts/rating-audit/2026-10-22/REVIEW_HANDOFF.md) under the current operating loop. Grok retest and an independent reviewer from an approved provider remain required; DeepSeek is prohibited. Keep all named gates unchanged. No production write, merge or deploy is authorised by this recommendation. [Report](../artifacts/rating-audit/2026-10-22/REPORT.md).


# UNFINISHED.md

## 2026-10-22 rating audit follow-up — explicitly unfinished

The requested targeted website audit and deployed Brief source trace are recorded in [REPORT.md](../artifacts/rating-audit/2026-10-22/REPORT.md). The frozen packet includes all 30 IDs, 150 successful page/API requests, original checksum-matched ODS, per-record source/date/label/filter/timestamps, reader reproduction and review handoff.

Unfinished: implement/review the proposed Brief resolved-rating contract; resolve four stale API-first conflicts, two current/inherited exceptions and one post-snapshot rating; establish the actual file cutoff; confirm hosting-to-database targeting; independently retest and challenge the evidence; exercise complete generated customer PDF/CSV/JSON and scope consistency. No whole-database website accuracy, absence of historic/provider/service-level ratings, actual runtime Brief generation or customer delivery is established. Domain/provider imports and scheduling/freshness alerts were not implemented. No production data, gates, merge or deploy changed. Current AGENTS.md prohibits DeepSeek; older mentions below are historical.

