#!/usr/bin/env python3
"""Shared helpers for the CQC directory ETL pipeline."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_for_logs() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def normalize_whitespace(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def flatten_json(data: Any, parent: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten nested dict/list structures into scalar or JSON-string values."""
    flattened: dict[str, Any] = {}

    if isinstance(data, dict):
        for key, value in data.items():
            key = str(key)
            new_key = f"{parent}{sep}{key}" if parent else key
            if isinstance(value, dict):
                flattened.update(flatten_json(value, new_key, sep))
            elif isinstance(value, list):
                flattened[new_key] = json.dumps(value, ensure_ascii=True)
            else:
                flattened[new_key] = value
        return flattened

    if isinstance(data, list):
        flattened[parent or "value"] = json.dumps(data, ensure_ascii=True)
        return flattened

    flattened[parent or "value"] = data
    return flattened


def deep_get(data: Any, path: str, default: Any = None) -> Any:
    """Get nested values from dict/list using dot-separated paths."""
    if data is None:
        return default
    if not path:
        return data

    current: Any = data
    for token in path.split("."):
        if isinstance(current, dict):
            if token in current:
                current = current[token]
            else:
                return default
        elif isinstance(current, list):
            if token.isdigit():
                index = int(token)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return default
            else:
                return default
        else:
            return default

    return default if current is None else current


def first_non_empty(data_candidates: Iterable[tuple[Any, str]] | Iterable[Any], default: Any = "") -> Any:
    """Return first non-empty candidate from values or (obj, path) tuples."""
    for candidate in data_candidates:
        if isinstance(candidate, tuple) and len(candidate) == 2:
            value = deep_get(candidate[0], candidate[1], None)
        else:
            value = candidate

        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        return value

    return default


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                parsed = json.loads(cleaned)
                return ensure_list(parsed)
            except Exception:
                pass
        parts = [part.strip() for part in cleaned.split("|") if part.strip()]
        return parts if parts else [cleaned]
    return [value]


def parse_any_date(value: Any) -> str:
    """Parse date-like values into YYYY-MM-DD; return empty string if invalid."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return ""
    text = str(value).strip()
    if not text:
        return ""

    text = text.replace("Z", "+00:00")
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return ""


def as_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
