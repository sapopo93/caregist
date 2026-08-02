# DELIVERABLE RETURN — NotebookLM operating procedure for first-revenue work

## What was produced
A governed NotebookLM operating procedure designed to support first-settled-revenue work while preventing duplication and data leakage. It includes:
- notebook taxonomy
- approved source-pack workflow
- research questions
- output templates
- handoff back to company-os
- quality/citation checks
- 30-day success measures
- initial recommended notebooks for CareGist, Leadgen SA, and public compliance research

## Procedure

### 1) Scope and guardrails
Use NotebookLM only for **public or sanitised sources** that support first-revenue decisions. Prioritise evidence that helps the team reach the first paying customer faster, but do **not** promise revenue outcomes.

**No-touch boundaries:**
- no NotebookLM creation performed here
- no Drive writes or file moves
- no customer/prospect/mailbox data
- no external contact
- no pricing recommendations
- no publishing actions

**Operating rule:** NotebookLM is a research and synthesis layer, not a system of record. Anything operationally sensitive stays in company-os, not inside the notebook.

### 2) Notebook taxonomy
Create a small number of purpose-built notebooks with a single decision job each. Keep overlap low.

| Notebook | Purpose | Allowed source types | Main output |
|---|---|---|---|
| CareGist | First revenue evidence | public URLs, public docs, sanitised internal notes | decision memo, buyer pain map, proof gaps |
| Leadgen SA | Lead-gen operating evidence | public URLs, sanitised internal notes | channel map, workflow risks, operational checklist |
| Public compliance research | public policy / legal guardrails | public regulator guidance, public platform policies, public standards | compliance note, red-flag list, do/don’t list |

**Deduplication rule:** one active notebook per decision object. If the same source is relevant to more than one notebook, reference it once in the source registry and link the notebook outputs back to that registry entry instead of duplicating the source pack.

### 3) Approved source-pack workflow
Use one source pack per question, not one source pack per person.

**Step A — Define the question**
Write a single-line question in the form:
> What evidence changes the next revenue decision?

**Step B — Preflight the sources**
Approve only sources that are:
- public web URLs, public PDFs, public policy pages, or sanitised internal docs
- directly relevant to the question
- free of personal data, customer data, credentials, and mailbox content
- unique enough to avoid repeated evidence across notebooks

**Step C — Build the pack**
Each source-pack entry should record:
- source title
- URL or file ID
- source type
- provenance
- sanitisation status
- notebook name
- reason included
- freshness date

**Step D — Import once**
Import the source pack into the correct notebook only once. Do not re-upload the same file into multiple notebooks when a single referenced source registry entry will do.

**Step E — Tag the pack**
Tag each pack by:
- notebook
- question
- date
- owner
- version

**Step F — Freeze the pack**
After the pack is approved, avoid adding new sources mid-analysis unless the question changes. New evidence means a new pack version.

### 4) Research questions by notebook

#### CareGist — first revenue evidence
Focus on the shortest path to a first paying customer.
Suggested questions:
- What buyer pain is urgent enough to trigger a purchase decision soon?
- Which workflow bottlenecks are repeatedly mentioned in public sources?
- Which segments show clear operational pain and low adoption friction?
- What proof artifacts would reduce buyer hesitation fastest?
- What delivery step is most likely to delay a first deal?

#### Leadgen SA — operating evidence
Focus on repeatable lead-generation mechanics and handoff quality.
Suggested questions:
- Which acquisition workflows are public, repeatable, and low-leakage?
- Where do leads get lost between discovery, qualification, and follow-up?
- What operational controls prevent duplicate work and bad handoffs?
- Which signals indicate the lead-gen motion is weak or too manual?
- What evidence shows the process is ready for controlled scale?

#### Public compliance research — guardrails
Focus on what must not be violated.
Suggested questions:
- Which public rules govern the intended workflow?
- What data classes are prohibited from entering NotebookLM?
- What claims would require stronger evidence before use?
- What disclosure or consent constraints apply to the workflow?
- What is the safest operational wording for internal handoff notes?

### 5) Output templates
Use one of the following formats for every notebook run.

#### A. Decision memo template
- Question
- Sources used
- What the evidence says
- What it does not say
- Recommended next action
- Confidence level
- Open questions
- Compliance flags

#### B. Source map template
- Source ID
- Title
- Type
- Why it matters
- Notebook
- Duplicate risk
- Sanitisation status

#### C. Revenue-readiness template
- Buyer pain
- Evidence strength
- Delivery friction
- Proof gaps
- Fastest next test
- Blockers

#### D. Compliance note template
- Rule or policy
- Source citation
- Impact on the workflow
- Required control
- Do-not-do list

### 6) Handoff back to company-os
Every NotebookLM run should end with a short company-os handoff note that includes:
- the question answered
- the notebook name and pack version
- the decision-grade conclusion
- open questions
- compliance flags
- the next company-os owner
- whether the result is ready for human review

**Handoff rule:** do not hand off raw NotebookLM chat as the final output. Convert it into a concise company-os note with citations and a clear action request.

### 7) Quality and citation checks
Reject any output that fails one of these checks:
- no citation for a factual claim
- a claim is supported by only one weak source when two are needed
- source provenance is unclear
- a source contains personal, customer, mailbox, or regulated data
- the notebook answer drifts into pricing or publishing
- a conclusion is stronger than the evidence

**Minimum QA bar:**
- every factual claim is either cited or marked as inference
- critical claims have at least two corroborating public sources where possible
- the source pack is deduplicated
- no prohibited data entered the notebook
- no recommendation promises revenue

### 8) 30-day success measures
Track operational success, not revenue promises.

**Outcome indicators**
- number of decision memos delivered
- number of first-revenue blockers reduced or removed
- number of notebook answers accepted by company-os on first pass
- percentage of outputs with complete citations
- number of duplicated sources avoided
- number of compliance flags caught before handoff

**Efficiency indicators**
- time from question to decision memo
- time spent cleaning sources before import
- percentage of packs requiring rework
- average number of sources per pack
- notebook reuse rate without duplication

**Quality indicators**
- citation completeness rate
- QA pass rate
- number of uncited claims found in review
- number of privacy/compliance escalations

**30-day target shape**
- faster question-to-memo cycle
- fewer duplicated sources
- zero prohibited-data incidents
- clearer handoff notes
- more first-revenue blockers identified early

## Initial recommended notebooks

### 1) CareGist | First revenue evidence
**Why this notebook exists:** to identify the shortest path to a first settled customer based on public and sanitised evidence.

**Use for:**
- buyer pain analysis
- proof-gap analysis
- operational blockers
- first-revenue prioritisation

**Avoid:**
- pricing decisions
- customer-specific records
- any external outreach plans

### 2) Leadgen SA | Operating evidence
**Why this notebook exists:** to understand the lead-generation motion, workflow reliability, and handoff quality.

**Use for:**
- acquisition workflow analysis
- duplication prevention
- qualification logic
- operational control checks

**Avoid:**
- mailbox data
- prospect identities
- live outreach content

### 3) Public compliance research | Guardrails and claims
**Why this notebook exists:** to keep the operating motion inside public-source, public-claim boundaries.

**Use for:**
- public policy and regulator guidance
- data-handling constraints
- claims review
- consent/privacy guardrails

**Avoid:**
- private customer data
- internal confidential records
- legal conclusions without qualified review

## Assumptions made
- Public and sanitised sources are sufficient for the first-pass NotebookLM workflow.
- The highest value comes from a small number of tightly scoped notebooks rather than a broad research library.
- Company-os remains the authoritative place for decisions, ownership, and final handoff.

## Known weaknesses / open questions
- NotebookLM can still drift if a source pack is too broad or too large; this requires disciplined source-pack versioning.
- Public-only research may miss operational context hidden in private systems, but that is the correct trade-off for this phase.
- If a source is later updated in Drive, NotebookLM may auto-sync changes, so source freeze discipline matters.

## Compliance flags
- No personal, customer, or mailbox data may enter NotebookLM.
- No pricing recommendations should be authored in this workflow.
- No publishing or outbound contact should be triggered from NotebookLM output alone.
- Public notebooks and featured notebooks may have account-type limitations; sharing must be treated as a controlled disclosure.
- NotebookLM outputs are AI-generated and must not be treated as legal, financial, or compliance advice without review.

## Evidence used
- Google Support: NotebookLM source types, Google Drive import, web URL import, Fast Research, Deep Research, and auto-sync behaviour.
- Google Support: public notebooks / featured notebooks and accepted-use guidance.
- Google Workspace product page: NotebookLM uses uploaded sources, provides citations for verification, and keeps uploaded data private unless shared.

## Ready for QA
**Yes.**

## Source references
- Google Support — Add or discover new sources for your notebook: https://support.google.com/gemininotebook/answer/16215270?hl=en-ZA&co=GENIE.Platform=Desktop
- Google Support — Use public notebooks and featured notebooks in Gemini Notebook: https://support.google.com/gemininotebook/answer/16322204?hl=en-ZA
- Google Workspace — Gemini Notebook for business: https://workspace.google.com/products/gemini-notebook/
