# Proof brief 3 — provider identity and moderation

Status: ready for Human Gate 1 review; internal only.

## Proposition

A provider listing can be protected from takeover by separating authenticated
identity, organisation authority evidence and final moderation, retaining only
evidence fingerprints and expiring verification.

## Controlled proof

- Use synthetic claimant/provider records only.
- Reject mismatched account email, missing identity evidence, missing authority
  evidence, expired evidence and same-person verification/moderation.
- Approve only when both evidence classes are current and the moderator is independent.
- Demonstrate suspension/re-verification path and retention anonymisation.

## Acceptance evidence

- Migrations 041–042, claim router/admin readiness checks and tests.
- Claim intake and remote provider media remain false by default.
- Raw proof content is fingerprinted before claim-record storage.

## Human Gate 1 decision requested

Approve or reject drafting the operational verification procedure; name the
controller, verifier, moderator, privacy owner and escalation deputy. Do not
activate provider claims or contact providers.

## Residuals

Acceptable evidence types, assurance level, document handling channel, appeal,
conflict management, safeguarding and legal basis need qualified approval.
