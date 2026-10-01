# Advisory operational report triage

Jev reads a supplied report and returns four structured judgments: operational
state, next step, action owner, and whether independent review is **reported**.
This is a local, opt-in tool. It does not verify live systems, execute actions,
change commercial gates, or approve its own work. Every result requires human
review. A reported independent check is a statement in the source, not proof that
the check happened.

## Run

From the repository root, preview a reviewed text report without an SDK, API key,
or network call:

```sh
python3 -m tools.jev_report_triage path/to/report.txt
```

For a paid advisory request, install the optional dependency in a local environment
and supply `TYPESAFE_API_KEY` through your existing secret manager/environment:

```sh
python3 -m pip install -r tools/requirements-jev.txt
python3 -m tools.jev_report_triage path/to/report.txt --live
```

`--live` sends the entire supplied report to TypeSafe. Use a reviewed extract with
no credentials or unnecessary personal data. Preview prints the proposed request,
including source text; live output contains a source hash and judgments, not the
report body. The SDK can log request bodies at debug level; leave SDK debug logging
off for private reports. The tool never loads `.env` automatically.

All four questions run in one request. The model is pinned to `jev-1.13.0`, retries
are disabled, and the SDK HTTP timeout is ten seconds. Empty reports and reports
over 32,000 UTF-8 bytes are rejected before any API call. Trivial questions and
deterministic calculations should use ordinary code, outside this report workflow.

Output includes the source SHA-256, schema and model, latency, available input
token usage, estimated input cost, and fields requiring closer review. Unknown
answers and confidence below 0.8 are flagged. This provisional threshold is not
calibrated on CareGist data. Invalid or unavailable responses return no judgments,
require manual review, and exit with code 2. They never become a green verdict.

The cost estimate uses the published $0.042 per million input tokens checked on
1 October 2026; output tokens are free. Missing usage produces a null estimate.
This is not a billing record. See https://docs.typesafe.ai/models and
https://docs.typesafe.ai/sdk/python/api/clients/sync for the provider contract.

## Measure usefulness on unseen reports

Use reports that were not used to design these questions. Before viewing Jev's
answers, have a separate reviewer assign the four expected labels using the
criteria in `tools/jev_report_triage.py`. Freeze that labelled set before running
predictions. Do not use the old keyword rules or deliberately poor hardcoded
actions as the baseline for a capable agent.

Save one live JSON result per line in `predictions.jsonl`. Prepare `labels.jsonl`
with one object per report, keyed by the exact source hash returned by the tool:

```json
{"report_sha256":"<64-character SHA-256>","expected":{"operational_state":"degraded","next_step":"investigate","action_owner":"agent","independent_review":"absent"}}
```

To measure time, use independent reviewers or counterbalance comparable report
sets to limit familiarity effects. Record actual elapsed manual review time as
`baseline_review_seconds` and actual review/correction time after seeing Jev as
`assisted_review_seconds`, on the same label object. Assisted time excludes API
waiting time; the evaluator adds recorded request latency. Include fallback review
time when a request fails. Omit both fields if no genuine timing observation exists.

```sh
python3 -m tools.jev_evaluate labels.jsonl predictions.jsonl
```

The evaluator reports label accuracy, failed requests, uncertain reports, and net
review seconds saved. Failures and missing answers count as incorrect, negative
time savings remain negative, and untimed runs return null savings. Duplicate
reports, missing report pairs, partial labels, and invalid timing are rejected.
It cannot certify that human labels or timing observations are independent. Keep
raw labels, frozen predictions, and reviewer identities privately for an independent
assessment; benchmark output is not production approval.

No report corpus, historic customer material, credentials, or fabricated savings
are included in this change. The offline tests verify contracts and failure paths;
they do not measure Jev's accuracy. Run them without network access:

```sh
python3 -m unittest discover -s tests -p test_jev_report_triage.py -v
```
