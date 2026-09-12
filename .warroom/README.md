# .warroom — CareGist completion status

**Authoritative status record for the CareGist 2026-09-11 completion target.**
Owned by: `ai-company-governed` (Chief of Staff). Sole portfolio dispatcher.

**Freshness stamp:** content verified against live production on **2026-09-11 00:07–00:30 BST**.
Previous stamp: 2026-08-20 (22 days stale). If this stamp is more than 7 days old, treat every
claim below as `NOT VERIFIED` and re-run the evidence commands in `CURRENT_VERDICT.md`.

## Files
| File | Purpose |
|---|---|
| `CURRENT_VERDICT.md` | Verified current truth; per-layer "running" definitions; readiness gate |
| `STATUS_BOARD.md` | Prioritised board: workstream, owner, evidence, status |
| `TOP_BLOCKERS.md` | Ranked blockers with class, severity and fix class |
| `NEXT_ACTIONS.md` | The next action per workstream + founder decision list |
| `UNFINISHED.md` | Known-incomplete work, explicitly labelled |
| `PIPELINE.md` | Collection → publication → sale → fulfilment pipeline state |
| `completion/` | Historical completion records |

## Evidence rule
Every claim in this directory carries raw evidence: an endpoint, a command, a hash, a run ID
or a test result. Status is only `DONE`, `ACTIVE`, `BLOCKED` or `PARKED`.
Evidence verdicts are `PASS`, `FAIL`, `PARTIAL`, `NOT VERIFIED` and are separate from status.

## Non-negotiables carried in this record
- Money-affecting and customer-facing actions require Henry's explicit approval:
  merging, production deployment, live Stripe changes, live data mutation, outbound messages.
- Uncommitted work is preserved before any repository operation.
- `caregistops.co.uk` is out of scope for this effort. Scope is CareGist and
  `caregist.co.uk`.
