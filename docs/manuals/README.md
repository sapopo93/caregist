# CareGist manuals

Updated 15 October 2026. These are the current instructions for customers, staff and sales. They supersede conflicting instructions in older training packs; dated audits and their reviews remain historical evidence. A manual describes the process and does not grant permission to contact prospects, take payment or release a customer pack.

| Reader | Start here | Outcome |
| --- | --- | --- |
| Directory user or prospective buyer | [User manual](USER_MANUAL.md) | Search, interpret a record, enquire and use an agreed delivery |
| Sibongile, Henry and trainer | [Training manual](TRAINING_MANUAL.md) | Practise the roles, stopping rules and handover |
| Sales and growth team | [Sales GTM manual](SALES_GTM_MANUAL.md) | Qualify the two current offers and measure real progress |
| Authorised CRM agent or manager | [CRM manual](CRM_MANUAL.md) | Work records, calls, tasks and permission controls |
| Commercial owner and release operator | [Operations manual](OPERATIONS_MANUAL.md) | Check gates, make and review a pack, release and recover |

The Markdown files are the maintained source. [The printable edition](CareGist_Manuals.pdf) contains all five manuals. Rebuild it with `build_manuals.py` using the bundled document runtime; editable Word output is generated locally alongside the PDF. Buyer records, payment evidence, prospect lists and customer packs belong in approved private systems.

## What the release evidence establishes

The [15 October public observations](../../artifacts/releases/2026-10-15/pre-release-public.json) recorded frontend and backend at `2332889fd4c77b7eed17f839b6d33b949eb3eec2`, working database directory access, degraded source health, `checkoutReady=false` and delivery disabled. The anonymous export request returned 401, requiring a token; this neither proves a paid export works nor proves every export flag is disabled. CRM redirected an anonymous visitor to login. Its health payload reported calling enabled but recording, AI and TPS automation disabled; no authenticated call or campaign was tested.

The latest saved [nightly report](../../artifacts/cqc-nightly/2026-10-15-report.md) is a separate, dated diagnostic. Its primary-workflow cadence calculation does not establish combined primary and backup schedule coverage. Its source alignment findings must not be dismissed because availability smoke passes. No new source reconciliation or live data repair is authorised by updating these manuals.

Use the [release record](../../artifacts/releases/2026-10-15/RELEASE.md) for the final commit, checks and deployment outcome. A successful software deployment does not pass the commercial gates.

## Source and ownership rules

Published catalogue and implementation: [catalogue configuration](../../frontend/lib/caregist-config.ts), [prices](../../frontend/lib/territory-scope.ts), [pricing page](../../frontend/app/pricing/page.tsx), [Brief page](../../frontend/app/territory-opportunity-brief/page.tsx). Operating design: [11 October plan](../../artifacts/final-operating-plan/2026-10-11/FINAL_PLAN.md), [journey](../../artifacts/customer-journey/2026-10-11/ENQUIRY_TO_RECEIPT.md) and [original training](../../artifacts/training/2026-10-11/TRAINING.md).

Henry owns commercial decisions, route approvals and escalation. Sibongile owns the staffed customer queue and records when assigned. A competent reviewer who did not produce or curate the pack reviews each final release. Reviewer and backup appointments must be evidenced; naming roles here does not staff them.

When behaviour, price or policy changes, update the affected source manual, rebuild the printable edition, independently review consequential claims and record the exact release evidence. Preserve older dated evidence without silently changing its reviewed contents.
