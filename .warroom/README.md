# CareGist War Room

Persistent state for the CareGist loop. A later `CONTINUE` starts here. Do not repeat closed work.

```
Grok 4.6 xhigh  (investigate / re-test)
    ↓
persist evidence into .warroom/
    ↓
checkpoint before turn exhaustion (cap 120)
    ↓
CONTINUE
    ↓
Codex fixes
    ↓
Grok 4.6 xhigh re-tests
    ↓
DeepSeek challenges the frozen evidence
    ↓
Hermes orchestrates the next bounded step
```

Hermes is the conductor. Grok does not mark itself green. Codex does not approve its own fix. DeepSeek does not raise an evidence tier.

## Files

| File | Role |
|---|---|
| `PIPELINE.md` | Role, model, and authority for each step |
| `CURRENT_VERDICT.md` | What is true, what is blocked, decision |
| `TOP_BLOCKERS.md` | What stops the next CareGist increment |
| `NEXT_ACTIONS.md` | Ordered next move + required approval |
| `UNFINISHED.md` | Open investigations |

## Checkpoint rule

Do not consume the 120-turn budget on purpose.

Before approaching the limit:

1. stop new investigations;
2. persist findings here;
3. update the four state files;
4. return a concise checkpoint summary.

Checkout, collectors, outbound delivery, and other fail-closed capabilities stay closed unless a named gate file says otherwise.
