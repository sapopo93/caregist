"""UK postcode / outward-code geocoding for public Find Care."""

from __future__ import annotations

import re

_FULL_POSTCODE_RE = re.compile(
    r"^([A-Z]{1,2}\d[A-Z\d]?)(\d[A-Z]{2})$",
    re.IGNORECASE,
)
_OUTWARD_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?$", re.IGNORECASE)


def compact_uk_postcode(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def is_uk_outward_code(value: str) -> bool:
    compact = compact_uk_postcode(value)
    if _FULL_POSTCODE_RE.fullmatch(compact):
        return False
    return bool(_OUTWARD_RE.fullmatch(compact))


def postcodes_io_lookup_path(value: str) -> str:
    """Return the postcodes.io path to try first."""
    compact = compact_uk_postcode(value)
    if is_uk_outward_code(compact):
        return f"/outcodes/{compact}"
    return f"/postcodes/{compact}"


def postcodes_io_fallback_path(value: str) -> str | None:
    """If a full-postcode lookup failed, try the outward district."""
    compact = compact_uk_postcode(value)
    if is_uk_outward_code(compact):
        return None
    full = _FULL_POSTCODE_RE.fullmatch(compact)
    if full:
        return f"/outcodes/{full.group(1).upper()}"
    if _OUTWARD_RE.fullmatch(compact):
        return f"/outcodes/{compact}"
    return None
