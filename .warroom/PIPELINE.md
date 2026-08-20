# CareGist model pipeline

Hermes owns the queue. Models do not vote.

| Step | Who | Model | Writes | Must not |
|---|---|---|---|---|
| 1 Investigate | Grok | grok-4.6 · reasoning **xhigh** · max 120 turns | `.warroom/` + dated evidence under `runs/` or `artifacts/` | Enable checkout, spend, deploy, contact |
| 2 Checkpoint | Hermes / Grok | same session | `CURRENT_VERDICT.md`, `TOP_BLOCKERS.md`, `NEXT_ACTIONS.md`, `UNFINISHED.md` | Start a new investigation in the checkpoint turn |
| 3 CONTINUE | Henry | — | — | Implied approval to resume only the next action |
| 4 Fix | Codex | gpt-5.6-sol via openai-codex | Code + tests in this repo | Declare the product green; change live pricing; open fail-closed flags |
| 5 Re-test | Grok | grok-4.6 xhigh | Step-level journey log | Trust Codex’s report; skip failure paths |
| 6 Challenge | DeepSeek | deepseek-v4-pro on a **frozen** packet | Challenge packet only | Edit the packet; raise an evidence tier |
| 7 Orchestrate | Hermes | this conductor | Next bounded action or HOLD | Run two commercial experiments at once |

## Freeze rule

DeepSeek receives a frozen packet: claim, URLs, dates, test log, what was not tested. If the packet changes after dispatch, the challenge is void.

## Green rule

No path is green until Grok has reproduced it after the Codex fix **and** DeepSeek has failed to kill the evidence. Unit tests and scheduler `completed` are not green.

## Fail-closed commercial rule

Radar checkout, source collectors, outbound delivery, leads, claims, and exports stay default-off. A vendor key is not approval.
