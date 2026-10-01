#!/usr/bin/env python3
"""Evaluate saved advisory predictions against separately prepared labels. No API calls."""

import argparse
import json
import math
import sys
from pathlib import Path

from tools.jev_report_triage import QUESTIONS, SCHEMA


def load_rows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError("Input file is empty")
    keyed = {}
    for row in rows:
        key = row["report_sha256"]
        if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("Invalid report hash")
        if key in keyed:
            raise ValueError("Duplicate report hash; keep one prediction per report")
        keyed[key] = row
    return keyed


def nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def evaluate(labels, predictions):
    if not labels or set(labels) != set(predictions):
        raise ValueError("Labels and predictions must cover exactly the same nonempty report set")
    correct = total = unavailable = 0
    timed = []
    review_total = 0
    for key, label in labels.items():
        expected = label["expected"]
        if set(expected) != set(QUESTIONS) or any(value not in QUESTIONS[q]["criteria"] for q, value in expected.items()):
            raise ValueError("Every report needs valid expected labels for all questions")
        prediction = predictions[key]
        if prediction.get("schema") != SCHEMA or prediction.get("mode") != "advisory" or prediction.get("status") not in ("ok", "unavailable"):
            raise ValueError("Invalid prediction schema or status")
        failed = prediction["status"] == "unavailable"
        unavailable += failed
        for question, value in expected.items():
            total += 1
            correct += not failed and prediction.get("answers", {}).get(question, {}).get("label") == value
        review_total += bool(prediction.get("uncertain_fields")) or failed
        baseline = label.get("baseline_review_seconds")
        assisted = label.get("assisted_review_seconds")
        if baseline is not None or assisted is not None:
            if not nonnegative(baseline) or not nonnegative(assisted) or not nonnegative(prediction.get("latency_ms")):
                raise ValueError("Timing requires nonnegative baseline, assisted review, and request latency")
            # Failed calls also cost time; assisted time must include fallback/manual review.
            timed.append(baseline - assisted - prediction["latency_ms"] / 1000)
    return {
        "reports": len(labels), "correct_labels": correct, "total_labels": total,
        "label_accuracy": correct / total, "unavailable_reports": unavailable,
        "reports_with_uncertainty": review_total,
        "timed_reports": len(timed),
        "net_review_seconds_saved": sum(timed) if timed else None,
        "production_savings_verified": False,
        "note": "Labels and timings are supplied observations. This evaluator does not certify their independence or production impact.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(load_rows(args.labels), load_rows(args.predictions))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
