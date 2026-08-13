# DELIVERABLE RETURN — CareGist Radar current weekly directory-delta alert

## Status

**BLOCKED**

- Named blocker removed: **No**.
- Exact blocked gate: the two mandated official CQC CSV URLs were unavailable to unauthenticated direct GET from this run. The first source returned HTTP 403 twice (once through Python `requests`, once through `curl` with a browser-style user agent). Under the task brief's stop rule, public-source unavailability requires an immediate BLOCKED return with no further retrieval strategy or fabricated substitute.
- This return is the only task artifact created. The requested alert Markdown and DOCX were not created because no truthful exact-current delta could be computed.

## Baseline and scope evidence

- Authorised repository: `/Users/user/CareGist`
- Starting branch: `codex/cqc-freshness-evidence-release`
- Exact clean starting commit: `650df5de06d96ad395d6b4e0e9f5f544fd57ee3e`
- Pre-task tracked/untracked status: clean.
- Work outside the authorised repository: none.
- Production, remote, customer, payment, publishing and outreach state: unchanged.

## Source retrieval evidence

Mandated sources:

1. `https://www.cqc.org.uk/system/files/2026-08/05_August_2026_CQC_directory.csv`
2. `https://www.cqc.org.uk/system/files/2026-08/12_August_2026_CQC_directory.csv`

Observed attempts:

- Python `requests.get`, unauthenticated GET, redirects enabled, 120-second timeout: `403 Client Error: Forbidden` for the 05 August URL.
- `curl`, unauthenticated GET, redirects enabled, browser-style user agent: `HTTP=403`, `content-type=text/html; charset=UTF-8`, `bytes=0` written because `--fail` rejected the response, elapsed `0.082912s` for the 05 August URL.
- Evidence checkpoint time after stopping: `2026-08-13T00:10:01Z` UTC.
- Credential-bearing headers: none.
- Spend: £0 / ZAR0.
- The 12 August request was not made after the second failure because `set -e` stopped the bounded retrieval command and the brief requires stopping after one non-progressing strategy/public-source unavailability.

## Acceptance evidence not obtainable

Because the official files were not retrieved, the following are truthfully **not available / not run**:

- Source hashes, preambles, schemas, row counts and unique location-ID counts.
- Addition, removal, territory and display counts.
- Zero-unchanged-ID and displayed-row membership checks.
- Deterministic local-authority territory selection.
- Claim-boundary, contact/PII and minimisation scans of a generated alert.
- Markdown structure checks.
- DOCX creation and ZIP/`word/document.xml` verification.
- Focused generator tests (no generator logic was changed).
- Independent DeepSeek review; eligibility requires a successful exact-current PII-free output.

No source hash or count has been guessed, inherited from an older snapshot, or fabricated.

## Changed paths and local commit

- Changed path: `artifacts/radar-sample/2026-08-13-current-weekly-directory-delta-return.md`
- Local commit: recorded by the final invoking report after this file is committed; a Git commit cannot truthfully contain its own resulting hash.
- Alert Markdown: not created.
- Founder-openable DOCX: not created.

## Customer and cash effect

- Customer activation: none.
- Customer access: none.
- Cash effect: none.
- Commercial state: unchanged; the lack-of-current-timing-signal blocker remains.

## Unresolved Critical/High findings and gates

- **High / blocker:** official current CQC snapshot retrieval is unavailable from this execution route, so a truthful weekly delta cannot be produced.
- Price, offering approval, seller/IP and contracting authority, legal/privacy/terms, payment, production deployment, publication/outreach, customer access and every external act remain unresolved founder gates.
- Country Pack remains `verification-required`; production and external use remain blocked.

## Deployment and rollback

- Implementation state: blocked before implementation.
- Deployment state: not deployed; no remote or production action.
- Rollback: delete this return file or revert its single local commit. No data, runtime, schema, customer or infrastructure rollback is required.

## Reviewer and next human gate

- Producer self-check only; this is not independent QA.
- Required different-provider DeepSeek review was not run because the exact-current output qualification gate was not met.
- Next human/governance gate: provide an approved, still-official unauthenticated public retrieval route or a new governed brief. Do not approve publication or external use from this blocked run.
