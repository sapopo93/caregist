# Alert-channel test evidence

Copy this template into the controlled evidence system for each alert in `ops/alert-catalog.yaml`. A repository copy with blank fields is not proof of configuration or delivery.

- Alert ID:
- Environment:
- Provider configuration ID:
- Owner:
- Operator:
- Approver:
- Test started (UTC):
- Test completed (UTC):
- Deployed Git SHA:
- Trigger method and redacted input:
- Expected threshold/window:
- Observed detection time:
- Observed notification time:
- Recipient/channel:
- Deduplication verified (no duplicate page during continuous incident):
- Recovery notification/state verified:
- Rollback/escalation verified:
- Provider evidence document ID:
- Evidence SHA-256:
- Result: PASS / FAIL
- Discrepancies and follow-up:

Passing requires the signal to cross its threshold, reach the named operational recipient, remain deduplicated while unresolved, and resolve after recovery. Do not use real customer personal data or secrets in a test payload.
