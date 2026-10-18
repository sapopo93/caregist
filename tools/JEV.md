# Jev advisory router: LIVE CALLS DISABLED

Jev supplies typed choices; it does not execute actions or approve any product gate.
The router is a local development tool, separate from application dependencies.

## Setup

Use Python 3.10 or newer (the installed SDK 0.7.2 metadata requires >=3.10).
From the repository root:

```sh
python3 -m venv .jev-venv
.jev-venv/bin/python -m pip install -r tools/requirements-jev.txt
```

Set `TYPESAFE_API_KEY` in your shell environment or the ignored repository `.env`.
The fallback supports a simple `TYPESAFE_API_KEY=value` line, optionally quoted;
it does not parse shell expressions, `export` statements or inline comments.
Never commit credentials. The local environment and `.tmp/` logs are ignored.

## Usage and disclosure

```sh
.jev-venv/bin/python tools/jev_route.py --dry-run \
  --task "Choose the next documentation step" \
  --context "Public documentation needs a setup example" \
  --option document="Write the setup example" \
  --option defer="Defer pending more information"
```

Dry-run validates inputs and displays the exact state and options without loading
credentials, importing the SDK, making a paid call or writing a decision log.
Live calls are currently blocked in code regardless of API key availability.
LIVE CALLS ARE DISABLED. UK-only data residency and processing have not been independently
verified. The script must not send task, context or options to TypeSafe until this
verification is complete and formally approved. Use --dry-run for local validation only.

Live results contain a choice, confidence, worth-it judgment, usage and UTC time.
The local log stores the task and result; treat it as private and disposable.
Confidence is distribution concentration, not correctness or permission to act.
Connection/SDK failures exit without an advisory decision; do not infer approval.
The default SDK model is used; the model version is not pinned by this tool.

The comparison and Hermes scripts are preserved as ignored local experiments.
They have weak baselines; the Hermes demo depends on a private local fixture.
They are not reproducible benchmarks or evidence of Jev superiority.

## References and verification

- https://docs.typesafe.ai/llms.txt
- https://docs.typesafe.ai/primitives/choice
- https://docs.typesafe.ai/sdk/python

On October 1 the Choice documentation was accessible, but targeted Python SDK
pages were unavailable through the documentation reader. This integration retains
the installed SDK 0.7.2 interface that successfully handled the approved advisory
request. Offline checks cover input rejection, credential absence and API failure
handling; they do not independently verify model accuracy or product readiness.
