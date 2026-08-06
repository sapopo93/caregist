#!/usr/bin/env python3
"""Guard evidence-grade CareGist output language.

The scan is intentionally narrow: it blocks banned framing when used as a
provider/location/service label, while avoiding unrelated technical terms such
as CSP's 'unsafe-inline' or React's dangerouslySetInnerHTML.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SCAN_PATHS = (
    Path("api/routers"),
    Path("api/services"),
    Path("frontend/app"),
    Path("frontend/components"),
    Path("tools"),
)

SCANNED_SUFFIXES = {
    ".html",
    ".j2",
    ".jinja",
    ".js",
    ".jsx",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
}

EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "node_modules",
}
EXCLUDED_FILENAMES = {
    "evidence_language_guard.py",
}

BANNED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bad provider", re.compile(r"\bbad\s+provider(s)?\b", re.IGNORECASE)),
    ("poor provider", re.compile(r"\bpoor\s+provider(s)?\b", re.IGNORECASE)),
    ("failing provider", re.compile(r"\bfailing\s+provider(s)?\b", re.IGNORECASE)),
    ("dangerous provider", re.compile(r"\bdangerous\s+provider(s)?\b", re.IGNORECASE)),
    ("unsafe provider", re.compile(r"\bunsafe\s+provider(s)?\b", re.IGNORECASE)),
    ("failing location", re.compile(r"\bfailing\s+location(s)?\b", re.IGNORECASE)),
    ("dangerous location", re.compile(r"\bdangerous\s+location(s)?\b", re.IGNORECASE)),
    ("unsafe location", re.compile(r"\bunsafe\s+location(s)?\b", re.IGNORECASE)),
    ("unsafe care home", re.compile(r"\bunsafe\s+care\s+home(s)?\b", re.IGNORECASE)),
    ("dangerous care home", re.compile(r"\bdangerous\s+care\s+home(s)?\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class LanguageFinding:
    path: str
    line: int
    column: int
    phrase: str
    excerpt: str


def scan_text(path: str, text: str) -> list[LanguageFinding]:
    findings: list[LanguageFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for phrase, pattern in BANNED_PATTERNS:
            for match in pattern.finditer(line):
                findings.append(
                    LanguageFinding(
                        path=path,
                        line=line_number,
                        column=match.start() + 1,
                        phrase=phrase,
                        excerpt=line.strip(),
                    )
                )
    return findings


def _candidate_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            candidates = (path,)
        else:
            candidates = path.rglob("*")
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if candidate.suffix not in SCANNED_SUFFIXES:
                continue
            if candidate.name in EXCLUDED_FILENAMES:
                continue
            if EXCLUDED_PARTS.intersection(candidate.parts):
                continue
            yield candidate


def scan_paths(paths: Iterable[str | Path]) -> list[LanguageFinding]:
    findings: list[LanguageFinding] = []
    for path in _candidate_files(Path(p) for p in paths):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(str(path), text))
    return findings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan output surfaces for banned provider/location framing.")
    parser.add_argument("paths", nargs="*", type=Path, default=list(DEFAULT_SCAN_PATHS))
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    findings = scan_paths(args.paths)
    if not findings:
        print("Evidence language guard passed.")
        return 0

    print("Evidence language guard failed:", file=sys.stderr)
    for finding in findings:
        print(
            f"{finding.path}:{finding.line}:{finding.column}: "
            f"banned phrase {finding.phrase!r}: {finding.excerpt}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
