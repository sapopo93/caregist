# CareGist operations manual

Updated 15 October 2026. For the commercial owner, source owner, producer, independent reviewer and release operator. The process below is conditional on evidence and approvals. It does not enable checkout, collectors, delivery, leads, claims or exports.

## Establish ownership and gates

Use one approved restricted enquiry/order register and one private evidence folder per order. Assign an owner, backup and independent reviewer with actual access and reserved time. A producer, editor or curator cannot approve their own work. Henry records commercial decisions and release authority; a document or model verdict cannot grant them.

| Gate | Evidence required | Stop when absent |
| --- | --- | --- |
| G0 Staffed | Roster, inbox/register access, backup and reviewer slots | Paid delivery commitment |
| G1 Source and release | Deployed identity; approved edition, retrieval time/hash, freshness, coverage, exceptions and applicable source/shadow/latency approvals | Unsupported source use, feasibility or affected commercial action |
| G2 Scope fidelity | One supported geography, service/category/window, exclusions, ranking and distinct-provider set | Quantity guarantee or payment for unsupported scope |
| G3 Outreach | Authorised campaign, recipient/channel evidence, suppression and copy; applicable call screening | Marketing contact; service messages need their approved route |
| G4 Terms and money | Approved fee/tax/terms/date and merchant route; payment and recovery rehearsal | Payment request and live money operation |
| G5 Full rehearsal | Full-sized synthetic pack, timed work, independent rendered review, controlled real route/access, wrong-recipient denial and recovery | First paid commitment or payment request |
| G6 Each release | Accepted scope, matched paid status, reviewed final files/hashes, attribution, recipient and route authority | That specific order/version's release |

G0 to G5 precede a paid commitment. G6 follows verified payment and final production. A paper exercise, successful build or generated sample cannot substitute for these receipts. Current public observations are in the [manual index](README.md); recheck them before a consequential action.

Digest sales remain on hold until product-specific operative terms and fulfilment approval are evidenced. The Brief process below cannot supply those product-specific approvals.

## Take an enquiry through production

1. Record an actual incoming message, received time, reference, owner and next update date. A CTA click is intent only. A proposed response target is the next working day, subject to staffed capacity and authorised communications.
2. Ask only for missing qualification fields. Freeze the exact selection predicates, exclusions, counting unit and required files. Unsupported service/category mapping requires clarification, not a silent broadening.
3. Check an approved source edition and candidate set. Count distinct nonblank CQC provider IDs separately from locations. If 22 qualify for an agreed 25, rescope with buyer and commercial approval or decline before payment. Do not pad.
4. Save the buyer's acceptance of a versioned scope: buyer decision, area, services, dates/window, exclusions, quantity, grouping/ranking rule, source/check date, files, recipient, fee/tax, terms and calendar deadline. Reserve the producer and reviewer slots.
5. After G0 to G5, the authorised owner issues one payment request through the selected approved route. Verify merchant status, amount, GBP currency, payer/order and refund state. A screenshot, email or redirect alone is insufficient. Reconcile uncertain, duplicate, mismatched or failed payments before retrying.
6. Produce from approved inputs and the accepted scope. Record time and source identity. Keep source facts, inference, prioritisation reason and unanswered qualification questions distinct. Existing generator code supports service filtering and qualification questions; the latest release also distinguishes absent rating-event dates. Do not infer that historical date fields were backfilled merely because the tool exists.

The Brief target is three English working days from the later scope/source check, counting the next working day as one. Payment verification precedes production and does not reset that clock. Retain the original date. If it is no longer achievable, Henry agrees a revised written calendar date with the buyer before production. Use current English holidays when calculating dates; training examples do not establish future availability.

## Review the actual pack

The independent reviewer opens the final PDF, CSV and manifest. Check every shortlisted provider against the accepted predicates and source records, including identity, relevant location scope, counts, links, dates, attribution and material gaps. A location rating must retain its proper scope. Scores or footprint do not establish buying intent.

Reconcile PDF and CSV counts and fields. Open the CSV in the intended application and inspect IDs, special characters, empty values, formulas and column mapping. Check the PDF's text, tables, page breaks and readable source trail. The manifest must identify the approved source editions, retrieval/check dates, hashes, attribution and reuse limits. A missing or old event date remains visible; collection time is not its replacement.

Record the exact filenames and SHA-256 hashes with the verdict. A changed final file needs re-review. Reject wrong territory, duplicates, unsupported claims, missing sources, unreadable layout or absent required files. Producer self-review is useful preparation and cannot supply the independent PASS.

## Release and establish receipt

At G6, match final hashes, paid entitlement, buyer-approved recipient and approved delivery route. Record explicit release authority and send/access evidence. Do not use dormant automated fulfilment as a bypass around independent review.

Ask the agreed recipient to open the PDF, CSV and manifest. Confirmed usable receipt remains pending until they confirm all three. An upload, queued email, provider send acceptance or tracking pixel is insufficient. Record scope acceptance after delivery separately from receipt; ask about usefulness five working days after confirmed access.

If delivery fails, own the issue and next update date. For a wrong recipient, stop further release, restrict access through the approved operator and escalate privately. For a factual defect, freeze affected release, correct against evidence and obtain independent re-review of the new hashes. Follow operative remedies; a template cannot grant refunds or invent deadlines.

## Operate the software release

Canonical production is the root Vercel multi-service configuration with Next.js frontend, FastAPI backend and Neon data. EC2/PM2 runbooks are historical. Use Stripe Projects CLI for managed provider/environment status; never publish generated credentials or local provider state.

Preserve dirty work before Git operations. Release current reviewed source through the configured Git/Vercel path. Check exact-commit CI, deployment target and status, then compare both `/api/v1/version` and `/api/health/directory` with the deployed commit. Exercise public paths and retain smoke evidence. Deployment success does not establish fresh data, working paid delivery or outreach permission.

Keep source reconciliation, main/backup polls, watchdog execution and notification receipt distinct. Inspect both signal workflows; a primary-only report cannot certify combined coverage. Keep the source's published date, retrieval date, reconciliation date and newest signal date separate. Do not launch a production backfill, migration, new collector or feature activation as a release verification step.

On failure, retain the failing logs and release identity, pause the affected path and assign an owner. Use an evidenced prior deployment for authorised software rollback; database recovery requires its own approved recovery procedure. Update the war-room checkpoint with unresolved work and evidence rather than marking the service commercially ready.
