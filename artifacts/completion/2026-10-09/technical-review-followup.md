**Blocking regression found in `52b72d1`: paid Brief delivery is also stopped by the outbound gate.**

The relevant caller contradicts the separate-outbox expectation: [territory_brief_fulfilment.py](/private/tmp/caregist-completion-20261009/api/services/territory_brief_fulfilment.py:324) inserts the paid download email into `pending_emails`. The new guard in [email_queue.py](/private/tmp/caregist-completion-20261009/api/utils/email_queue.py:115) blocks that queue when outbound is closed.

A mocked paid fulfilment reproduced: order marked `fulfilled`, download email queued, then **zero claims or sends** while outbound remained closed. No separate paid delivery outbox was used. This blocks acceptance of the requested paid-delivery contract.

The three named fixes otherwise passed targeted checks against source loaded directly from the commit:

- **Closed queue:** no DB access, claim, send, or pending-row changes.
- **Closure during claim:** row returned to pending; processing timestamp cleared; attempts and schedule preserved.
- **Reopening:** preserved row sent once with its original idempotency key.
- **Requested quantity:** PDF text and CSV matched distinct-provider counts: Isle of Wight **8/50**, Portsmouth **13/50**, Southampton **37/50**, **25/25**, and **10/10**. Shortfall notices followed the requested target.
- **Empty CSV:** generated zero-signal scope produced exactly one 22-column header and no data rows; PDF retained the **0/50** shortfall notice.

Bounded to this commit and relevant callers; 10 tool calls, no network, secret access, or persistent mutations. PDF bytes were rendered in memory and text extracted; visual layout was not checked.

**No commercial approval.** The failed independent Grok/DeepSeek reviews remain required and outstanding.