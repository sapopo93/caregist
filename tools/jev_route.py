#!/usr/bin/env python3
"""Ask Jev (TypeSafe System One) for a bounded next-step decision.

Shadow mode: the decision is advisory and logged to .tmp/jev-decisions.jsonl.
It never approves work or opens a fail-closed gate (see AGENTS.md).

Usage:
    .jev-venv/bin/python tools/jev_route.py --task "..." --option a="..." --option b="..." [--context "..."]
    .jev-venv/bin/python tools/jev_route.py --dry-run ...   # validate inputs, no API call
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / ".tmp" / "jev-decisions.jsonl"


def load_key() -> None:
    if os.environ.get("TYPESAFE_API_KEY"):
        return
    env = ROOT / ".env"
    if not env.is_file():
        sys.exit("Set TYPESAFE_API_KEY in the environment or repository .env")
    for line in env.read_text().splitlines():
        if line.startswith("TYPESAFE_API_KEY="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                os.environ["TYPESAFE_API_KEY"] = value
                return
    sys.exit("TYPESAFE_API_KEY not found in environment or .env")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True, help="What the agent is about to do")
    p.add_argument("--context", default="", help="Relevant facts, no secrets")
    p.add_argument("--option", action="append", required=True, help="key=description")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    options = {}
    for raw in args.option:
        if "=" not in raw:
            p.error("Each --option must use key=description")
        key, description = (part.strip() for part in raw.split("=", 1))
        if not key or not description:
            p.error("Option keys and descriptions must be nonempty")
        if key in options:
            p.error("Option keys must be unique")
        options[key] = description
    if len(options) < 2:
        p.error("Need at least two options")
    if not args.task.strip():
        p.error("Task must be nonempty")
    state = {"task": args.task, "context": args.context}

    if args.dry_run:
        print(json.dumps({"mode": "dry-run", "state": state, "options": options}, indent=2))
        return

    load_key()
    try:
        from typesafe_sdk import Choice, Noul, TypeSafeClient
    except ImportError:
        sys.exit("Install optional dependencies: python -m pip install -r tools/requirements-jev.txt")

    started = time.time()
    try:
        with TypeSafeClient() as client:
            r = client.system_one(
                state=state,
                questions={
                    "route": Choice(
                        instructions="Given `task` and `context`, which next step is most likely to make progress at the lowest wasted effort?",
                        criteria=options,
                    ),
                    "worth_it": Noul(
                        instructions="Is `task` substantial enough that choosing the approach carefully matters, rather than a trivial or deterministic step?"
                    ),
                },
            )
    except Exception as error:
        # API exception text may contain response or request details. Report only its type.
        sys.exit(f"Jev request failed ({type(error).__name__}); no decision was recorded")
    route = r.choices["route"]
    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow",
        "task": args.task,
        "choice": route.choice,
        "confidence": getattr(route, "confidence", None),
        "worth_it": r.nouls["worth_it"].noul,
        "latency_ms": round((time.time() - started) * 1000),
        "input_tokens": r.usage.input_tokens,
        "output_tokens": r.usage.output_tokens,
    }
    try:
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a") as f:
            f.write(json.dumps(result, default=str) + "\n")
    except OSError:
        sys.exit("Jev returned an answer but the local decision log could not be written")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
