#!/usr/bin/env python3
"""Mechanical migration governance checks for CareGist.

Historical migrations pre-date the reversible-migration rule, so this checker
enforces down-migration presence for migration numbers >= 036 while applying
the no-db-push and tenant/destructive safety checks repository-wide.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MIGRATION_RE = re.compile(r"^(?P<number>\d{3})_.+\.sql$")
DOWN_SUFFIX = ".down.sql"
BASELINE_REVERSIBLE_FROM = 36
LEGACY_DUPLICATE_MIGRATIONS = {
    34: frozenset({"034_named_care_groups_view.sql", "034_verification_token_expiry.sql"}),
}

DESTRUCTIVE_SQL_RE = re.compile(
    r"\b(DROP\s+(TABLE|COLUMN|SCHEMA|DATABASE)|ALTER\s+TABLE\s+\S+\s+ALTER\s+COLUMN\s+\S+\s+TYPE)\b",
    re.IGNORECASE,
)
TENANT_TYPE_RE = re.compile(
    r"\bALTER\s+TABLE\b[^;]*\btenant_id\b[^;]*\b(TYPE|SET\s+DATA\s+TYPE)\b",
    re.IGNORECASE | re.DOTALL,
)
PRISMA_DB_PUSH_RE = re.compile(r"\bprisma\s+db\s+push\b", re.IGNORECASE)

SKIP_PARTS = {".git", ".next", ".venv", "__pycache__", "node_modules"}
SKIP_FILENAMES = {"check_migration_governance.py", "test_migration_governance.py"}
TEXT_SUFFIXES = {".md", ".py", ".sh", ".sql", ".toml", ".yml", ".yaml", ".json"}


@dataclass(frozen=True)
class GovernanceFinding:
    rule: str
    path: str
    message: str


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_PARTS.intersection(path.parts):
            continue
        if path.name in SKIP_FILENAMES:
            continue
        if path.suffix in TEXT_SUFFIXES:
            yield path


def _migration_number(path: Path) -> int | None:
    match = MIGRATION_RE.match(path.name)
    if not match:
        return None
    return int(match.group("number"))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def check_governance(root: str | Path = ".") -> list[GovernanceFinding]:
    root_path = Path(root)
    findings: list[GovernanceFinding] = []
    approved_destructive = os.environ.get("APPROVED_DESTRUCTIVE") == "true"

    for path in _iter_text_files(root_path):
        text = _read_text(path)
        display = str(path)
        if PRISMA_DB_PUSH_RE.search(text):
            findings.append(
                GovernanceFinding(
                    "no_prisma_db_push",
                    display,
                    "`prisma db push` is forbidden; use explicit SQL migrations.",
                )
            )

    migrations_dir = root_path / "db" / "migrations"
    if not migrations_dir.exists():
        return findings

    down_dir = migrations_dir / "down"
    migration_paths = sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql"))
    migrations_by_number: dict[int, list[Path]] = {}
    for migration_path in migration_paths:
        number = _migration_number(migration_path)
        if number is not None:
            migrations_by_number.setdefault(number, []).append(migration_path)

    for number, paths in migrations_by_number.items():
        names = frozenset(path.name for path in paths)
        if len(paths) > 1 and LEGACY_DUPLICATE_MIGRATIONS.get(number) != names:
            findings.append(
                GovernanceFinding(
                    "duplicate_migration_number",
                    ", ".join(str(path) for path in paths),
                    f"Migration number {number:03d} is used by multiple files: {', '.join(sorted(names))}.",
                )
            )

    for migration_path in migration_paths:
        number = _migration_number(migration_path)
        if number is None:
            continue
        text = _read_text(migration_path)
        display = str(migration_path)

        if number >= BASELINE_REVERSIBLE_FROM:
            down_path = down_dir / f"{migration_path.stem}{DOWN_SUFFIX}"
            if not down_path.exists():
                findings.append(
                    GovernanceFinding(
                        "missing_down_migration",
                        display,
                        f"Migration {migration_path.name} requires {down_path}.",
                    )
                )

        if TENANT_TYPE_RE.search(text):
            findings.append(
                GovernanceFinding(
                    "tenant_id_type_change_forbidden",
                    display,
                    "tenant_id type changes are forbidden by the migration gate.",
                )
            )

        if number >= BASELINE_REVERSIBLE_FROM and DESTRUCTIVE_SQL_RE.search(text) and not approved_destructive:
            findings.append(
                GovernanceFinding(
                    "destructive_sql_requires_approval",
                    display,
                    "DROP or ALTER COLUMN TYPE requires APPROVED_DESTRUCTIVE=true.",
                )
            )

    return findings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check CareGist migration governance rules.")
    parser.add_argument("root", nargs="?", default=".")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    findings = check_governance(args.root)
    if not findings:
        print("Migration governance checks passed.")
        return 0

    print("Migration governance checks failed:", file=sys.stderr)
    for finding in findings:
        print(f"{finding.path}: {finding.rule}: {finding.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
