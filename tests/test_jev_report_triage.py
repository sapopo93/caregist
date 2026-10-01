"""Offline contract tests; these do not establish model accuracy."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.jev_evaluate import evaluate, load_rows
from tools.jev_report_triage import MAX_BYTES, QUESTIONS, triage


def response():
    return {
        "model": "jev-1.13.0",
        "usage": {"input_tokens": 1000},
        "choices": {
            key: {"choice": next(iter(spec["criteria"])), "confidence": 1.0,
                  "probabilities": {label: float(i == 0) for i, label in enumerate(spec["criteria"])}}
            for key, spec in QUESTIONS.items()
        },
    }


class TriageTests(unittest.TestCase):
    def test_single_batch_metadata_and_no_report_in_result(self):
        calls = []

        def call(request):
            calls.append(request)
            return response()

        result = triage("Private operational report", call)
        self.assertEqual(len(calls), 1)
        self.assertEqual(set(calls[0]["questions"]), set(QUESTIONS))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["human_review_required"])
        self.assertFalse(result["authorizes_action"])
        self.assertNotIn("Private operational report", json.dumps(result))
        self.assertAlmostEqual(result["estimated_input_cost_usd"], 0.000042)

    def test_invalid_input_never_calls_provider(self):
        for report in (" ", "x" * (MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                triage(report, lambda _: self.fail("Provider must not be called"))

    def test_error_does_not_echo_private_data(self):
        def call(_):
            raise RuntimeError("secret report body")
        result = triage("report", call)
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["answers"], {})
        self.assertNotIn("secret", json.dumps(result))

    def test_incomplete_or_invalid_response_fails_closed(self):
        for kind in ("missing", "label", "nan", "distribution", "tokens"):
            data = response()
            answer = data["choices"]["next_step"]
            if kind == "missing":
                del data["choices"]["next_step"]
            elif kind == "label":
                answer["choice"] = "enable_checkout"
            elif kind == "nan":
                answer["confidence"] = float("nan")
            elif kind == "distribution":
                answer["probabilities"] = {"investigate": 1.0}
            else:
                data["usage"]["input_tokens"] = -1
            with self.subTest(kind=kind):
                self.assertEqual(triage("report", lambda _, data=data: data)["status"], "unavailable")

    def test_unknown_or_low_confidence_is_flagged(self):
        data = response()
        data["choices"]["action_owner"]["confidence"] = 0.4
        answer = data["choices"]["next_step"]
        answer.update(choice="unknown", probabilities={key: float(key == "unknown") for key in answer["probabilities"]})
        result = triage("report", lambda _: data)
        self.assertEqual(set(result["uncertain_fields"]), {"action_owner", "next_step"})

    def test_absent_usage_is_not_reported_as_free(self):
        data = response()
        data.pop("usage")
        self.assertIsNone(triage("report", lambda _: data)["estimated_input_cost_usd"])

    def test_preview_works_without_sdk_or_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.txt"
            path.write_text("No action is outstanding.")
            # -S disables site packages, proving that preview needs no SDK.
            output = subprocess.check_output([sys.executable, "-S", "-m", "tools.jev_report_triage", str(path)], text=True)
            self.assertEqual(json.loads(output)["api_calls"], 0)


class EvaluationTests(unittest.TestCase):
    def data(self):
        prediction = triage("report", lambda _: response())
        key = prediction["report_sha256"]
        labels = {key: {"expected": {q: a["label"] for q, a in prediction["answers"].items()}}}
        return key, labels, {key: prediction}

    def test_missing_timing_never_invents_savings(self):
        _, labels, predictions = self.data()
        result = evaluate(labels, predictions)
        self.assertEqual(result["label_accuracy"], 1)
        self.assertIsNone(result["net_review_seconds_saved"])
        self.assertFalse(result["production_savings_verified"])

    def test_unavailable_predictions_count_against_accuracy_and_timing(self):
        key, labels, predictions = self.data()
        predictions[key].update(status="unavailable", answers={}, latency_ms=2000)
        labels[key].update(baseline_review_seconds=10, assisted_review_seconds=12)
        result = evaluate(labels, predictions)
        self.assertEqual(result["label_accuracy"], 0)
        self.assertEqual(result["net_review_seconds_saved"], -4)
        self.assertEqual(result["unavailable_reports"], 1)

    def test_missing_reports_and_partial_labels_rejected(self):
        key, labels, predictions = self.data()
        with self.assertRaises(ValueError):
            evaluate(labels, {})
        labels[key]["expected"].pop("next_step")
        with self.assertRaises(ValueError):
            evaluate(labels, predictions)

    def test_nan_and_partial_timing_rejected(self):
        key, labels, predictions = self.data()
        for value in (None, float("nan"), -1):
            labels[key].update(baseline_review_seconds=10, assisted_review_seconds=value)
            with self.assertRaises(ValueError):
                evaluate(labels, predictions)

    def test_duplicate_report_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"labels.jsonl"
            row = json.dumps({"report_sha256": hashlib.sha256(b"report").hexdigest()})
            path.write_text(row + "\n" + row + "\n")
            with self.assertRaises(ValueError):
                load_rows(path)


if __name__ == "__main__":
    unittest.main()
