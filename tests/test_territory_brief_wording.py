"""The Brief must not predict inspection timing or buying intent from a rating."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "api/services/territory_brief.py",
    ROOT / "api/services/territory_brief_render.py",
]
# Unqualified prediction wording. Negations such as "does not establish ... intent" are allowed.
BANNED = [
    r"before re-?inspection",
    r"re-?inspection (?:is |will be )?(?:likely|due|expected|imminent)",
    r"inspection (?:is |will be )?(?:likely|due|expected|imminent)",
    r"likely to (?:buy|purchase|need|be inspected)",
]


def test_no_timing_or_intent_predictions_in_generated_wording():
    for path in FILES:
        text = path.read_text()
        for pattern in BANNED:
            assert not re.search(pattern, text, re.IGNORECASE), f"{path.name}: {pattern}"
