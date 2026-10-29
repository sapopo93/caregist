# Territory Brief rating contract — queued review

Status: QUEUED locally, not dispatched or approved. No deploy is authorised.

1. Grok 4.6 xhigh: retest the frozen customer journey step by step against the original 22 October evidence, the source copy, generated fixture PDF/CSV/JSON and test receipts. Check rating-based scope and retries against the same edition. Do not repeat closed PR #122 work.
2. After that retest, an independent reviewer model from an approved provider must challenge this exact packet. Use a different model from the producing Codex model; DeepSeek is prohibited. Return PASS/FAIL/PARTIAL per promise with IDs and evidence references. Agreement alone is not green.
3. Hermes: choose the next single bounded step after these receipts. Commercial gates remain unchanged. No production writes, merges or deployments.

Queue owner: CareGist operating loop. There is no Grok or external-model execution receipt in this packet; this local queue must not be reported as an executed review.

A supplementary independent agent instance found scope/date/status regressions during implementation. They were corrected and rechecked; it found no remaining critical defects in those named findings. That review is not a substitute for either required operating-loop stage and inspected a working tree rather than this final sealed packet.

Review inputs: `MANIFEST.sha256`, `README.md`, `QUALITY_GATE.md`, `FIXTURE_RESULTS.md`, `source/`, `candidate.patch`, `fixtures.json`, `rating-evidence.json`, `brief.pdf`, `brief.csv`, `brief.json`, test receipts. Original source evidence: `artifacts/rating-audit/2026-10-22/REPORT.md`, `REVIEW_HANDOFF.md`, `MANIFEST.sha256`, raw API/HTML and `source/ratings.ods`.
