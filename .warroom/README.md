# .warroom — CareGist completion status

**Authoritative status record for the CareGist 2026-09-11 completion target.**
Owned by: `ai-company-governed` (Chief of Staff). Sole portfolio dispatcher.

**Freshness stamp:** re-verified against live production, GitHub Actions and the repository on
**2026-09-23 02:27–03:50 BST**. Previous full stamp: 2026-09-11.
If this stamp is more than 7 days old, treat every claim below as `NOT VERIFIED` and re-run the
evidence commands in `CURRENT_VERDICT.md`.

**2026-09-23 scope.** Read-only live probes confirmed frontend and backend both serve
`9ece88698b0a3a812d9a0a3af1a0fa17aaba091c` (= `origin/main`). GitHub run logs were inspected
for reconciliation, signal polls, smoke and the freshness watchdog. No deployment, live data
mutation, Stripe change, merge or outbound message was performed.

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
