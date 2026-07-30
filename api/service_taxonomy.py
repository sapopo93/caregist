"""Canonical service taxonomy backed by one versioned cross-stack registry."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "frontend" / "data" / "service-taxonomy.json"
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@lru_cache(maxsize=1)
def taxonomy() -> tuple[dict[str, Any], ...]:
    entries = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    slugs: set[str] = set()
    aliases: set[str] = set()
    for entry in entries:
        slug = entry["slug"]
        if not _SLUG_RE.fullmatch(slug) or slug in slugs:
            raise RuntimeError(f"Invalid or duplicate canonical service slug: {slug}")
        slugs.add(slug)
        for alias in entry["aliases"]:
            key = alias.casefold().strip()
            if not key or key in aliases:
                raise RuntimeError(f"Duplicate canonical service alias: {alias}")
            aliases.add(key)
    return tuple(entries)


@lru_cache(maxsize=1)
def _by_slug() -> dict[str, dict[str, Any]]:
    return {entry["slug"]: entry for entry in taxonomy()}


@lru_cache(maxsize=1)
def _by_alias() -> dict[str, dict[str, Any]]:
    return {
        alias.casefold().strip(): entry
        for entry in taxonomy()
        for alias in entry["aliases"]
    }


def resolve_service_filter(value: str | None) -> tuple[str, ...] | None:
    """Resolve a canonical slug or legacy raw label to exact source aliases."""
    if value is None or not value.strip():
        return None
    cleaned = value.strip()
    entry = _by_slug().get(cleaned) or _by_alias().get(cleaned.casefold())
    if entry:
        return tuple(alias.casefold() for alias in entry["aliases"])
    return (cleaned.casefold(),)


def canonical_service_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate legacy raw-label counts under stable canonical services."""
    counts: dict[str, int] = {}
    for row in raw_rows:
        label = str(row.get("service_type") or "").strip()
        entry = _by_alias().get(label.casefold())
        if not entry:
            continue
        counts[entry["slug"]] = counts.get(entry["slug"], 0) + int(row.get("provider_count") or 0)
    return [
        {
            "service_type": entry["slug"],
            "service_name": entry["name"],
            "category": entry["category"],
            "provider_count": counts.get(entry["slug"], 0),
            "source_aliases": entry["aliases"],
        }
        for entry in taxonomy()
        if counts.get(entry["slug"], 0) > 0
    ]
