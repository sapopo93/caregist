# CareGist CRM — sanitised DeepSeek V4 Pro audit packet

Date: 2026-08-13

This packet contains no credentials, customer data, recordings, transcripts, telephone numbers, or environment values. It is intended for a one-off independent architecture audit using a memory-only API credential.

## Audit question

Act as an independent principal security and release reviewer. Identify only substantiated P0, P1, or P2 defects. For each finding, state the violated invariant, concrete failure path, severity, and smallest safe remediation. Do not assume that feature flags, application RLS, provider callbacks, redaction, retention, or cost controls are correct merely because they exist. If evidence is insufficient, label it as an evidence gap rather than inventing a defect.

## Required invariants

- CRM data and child records remain organisation-scoped under forced PostgreSQL RLS.
- UK SMS cannot start enabled; all CRM capabilities default off.
- Calls require current TPS/CTPS evidence and no suppression at authorisation and dial boundaries.
- A user cannot start another call until the previous call has an operator-confirmed disposition.
- Twilio callbacks are signed, account-bound, bounded, idempotent, and safe when duplicated or reordered.
- Audio is private, encrypted, never stored in PostgreSQL, and inaccessible at its exact 30-day expiry.
- Local dual-channel Whisper labels the browser leg `Agent` and PSTN leg `Contact`; malformed or mono audio fails closed.
- Raw audio and unredacted transcripts never leave CareGist.
- Local redaction must remove names, contact data, identifiers, and sensitive content before DeepSeek.
- DeepSeek V4 Flash runs non-thinking, returns strict JSON, and cannot mutate compliance, employment, suppression, disposition, or pipeline state.
- Monthly AI spend uses a database-serialised hard cap, pessimistic ambiguous-charge accounting, and durable per-attempt usage evidence.
- Retention wins races with transcription/evaluation and produces deletion audit evidence.

## Architecture and trust boundaries

1. Authenticated browser → CareGist API → organisation-scoped PostgreSQL CRM.
2. CareGist API issues a short-lived, one-use opaque call authorisation; the browser never supplies the destination to Twilio.
3. Twilio Voice callbacks enter signed/account-bound endpoints and are serialised against suppression and call state.
4. Completed dual-channel recording metadata queues a worker. The worker bounds downloads, verifies SHA-256, writes private AES-256 object storage, then independently deletes Twilio's copy.
5. A dedicated CPU worker decodes and separates channels, runs `faster-whisper small.en int8`, performs mandatory local redaction/NER, then sends only redacted text with a pseudonymous HMAC identifier to DeepSeek.
6. Provider attempts are reserved under a PostgreSQL advisory transaction lock. Durable usage rows release one pessimistic hold; an unpersisted possibly charged request retains one worst-case hold. Active holds cross month boundaries, while failed holds expire from the following billing month.
7. Exact application access ends at `expires_at`; retention clears transcript/evaluation identifiers and deletes both object copies, with readiness failing on expired backlog.

The detailed Mermaid architecture is maintained in `docs/crm-twilio-pilot.md`.

## Relevant implementation excerpts (paraphrased)

- `api/routers/crm.py`: per-agent advisory lock before call creation; shared contact lock at suppression and voice dial gate; one-use hashed call tokens; Twilio signature and account SID checks; bounded callback bodies.
- `api/services/crm_transcription.py`: ffprobe/ffmpeg validation, stereo-only channel separation, spawn-isolated model process, concurrent queue drain, 900-second hard termination.
- `api/services/crm_ai.py`: 120,000-character bound; regex, known-entity, spaCy NER and conservative proper-name residual checks; exact DeepSeek origin/model; non-thinking JSON request; strict Pydantic response; three-attempt reservation; per-attempt ledger; conditional lease/expiry completion.
- `api/services/crm_retention.py`: expired-row claim, immediate AI-content purge, independent provider/object deletion, retryable error state and audit row.
- migrations 052–054: forced RLS, worker-specific policies, composite tenant foreign keys, call/retention constraints and reversible local rehearsal.
- `frontend/app/crm/page.tsx`: pinned contact while a call is unresolved; serialised call/disposition actions; four primary dispositions; conditional secondary choices; task/pipeline/report/review interfaces.

## Verification inventory

- Full Python suite under a non-superuser, non-`BYPASSRLS` PostgreSQL owner, including the real local Whisper model.
- Fresh-schema migration chain, 054 down→up rehearsal, forced-RLS owner/worker visibility, cross-tenant FK rejection, advisory-lock contention, retention purge and audit.
- Twilio invalid/missing signature, account mismatch, body-size, duplicate, stale and out-of-order contracts.
- Redaction adversarial casing, invented names, Unicode/local NER, contact identifiers and sensitive phrases; provider-spy boundary tests.
- Frontend unit tests, TypeScript, production build, authenticated Playwright operator flow, unresolved-disposition reload recovery, task/report flow, and axe accessibility scan.
- Ruff, migration governance, Compose config, dependency checks, npm audit, secret-pattern scan and diff whitespace check.

## Known external and business risks

- No provider credential was available for the one-off live Flash request or this Pro audit; neither has been executed.
- No funded/provisioned Twilio account or approved UK number was used; a supervised allowlisted call remains external.
- Licensed TPS/CTPS feed, recording/legal wording approval, private storage lifecycle, delivered alerts, worker hosting quote, and production activation approval remain external.
- At 1,000 five-minute calls/month, estimated metered cost is $154.54 total for three seats before VAT, dedicated CPU worker and private storage. The stated £30/seat target is not evidenced at that volume.

## Required response format

Return JSON only:

```json
{
  "verdict": "GO|NO_GO",
  "findings": [
    {
      "severity": "P0|P1|P2",
      "invariant": "string",
      "failure_path": "string",
      "remediation": "string"
    }
  ],
  "evidence_gaps": ["string"],
  "residual_risks": ["string"]
}
```
