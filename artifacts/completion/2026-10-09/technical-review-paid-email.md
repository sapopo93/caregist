Found one concrete race in HEAD `076f100`:

- **P2 — Refund after claim still permits delivery.** In `api/utils/email_queue.py`, SQL derives `paid_brief_delivery` during claim, then `_send_one` trusts that cached boolean. If the matching order changes from `fulfilled` to `refunded` before its send begins—including while waiting for the semaphore—the email still sends with outbound communications disabled. The send path rechecks the marketing flag, but not order eligibility. Add a test that refunds after claim and verify the email is deferred without spending a retry.

Otherwise, the inspected SQL uses exact key equality and matching customer email; caller-supplied prefixes cannot independently bypass the guard. Excluded marketing rows remain untouched, and the existing deferral path preserves attempts.

Scope: read repository instructions and reviewed only `git show HEAD`; no tests executed, network access, secrets, or mutations. The seven passing tests are user-reported evidence; the shown integration test covers orders already refunded before claim.

This is a technical recheck only. It does not approve release/product gates or replace the failed required Grok/DeepSeek reviews.