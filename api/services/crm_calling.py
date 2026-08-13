"""Pure CRM calling helpers and Twilio boundary validation."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Mapping
from urllib.parse import urljoin

from fastapi import HTTPException


E164_PATTERN = re.compile(r"^\+[1-9][0-9]{7,14}$")
TWILIO_CALL_SID_PATTERN = re.compile(r"^CA[0-9a-fA-F]{32}$")
TERMINAL_CALL_STATUSES = frozenset({"completed", "busy", "no_answer", "failed", "canceled"})


def normalize_e164(value: str | None) -> str | None:
    """Accept only already-normalised international numbers at this boundary."""
    if value is None:
        return None
    normalized = "".join(value.strip().split())
    if not E164_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=422, detail="Phone number must use E.164 format, for example +442071234567.")
    return normalized


def allowed_test_numbers(value: str) -> frozenset[str]:
    numbers: set[str] = set()
    for item in value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        if not E164_PATTERN.fullmatch(candidate):
            raise RuntimeError("CRM_ALLOWED_TEST_NUMBERS contains a number that is not valid E.164.")
        numbers.add(candidate)
    return frozenset(numbers)


def hash_call_authorization(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_twilio_call_sid(value: str) -> str:
    if not TWILIO_CALL_SID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=422, detail="Twilio CallSid is invalid.")
    return value


def hash_screening_number(phone_e164: str, key: str) -> str:
    """Create a keyed lookup digest so imported register numbers are not stored raw."""
    if len(key) < 32:
        raise RuntimeError("CRM screening hash key is not configured securely.")
    if not E164_PATTERN.fullmatch(phone_e164):
        raise ValueError("Screening number must use E.164 format.")
    return hmac.new(key.encode("utf-8"), phone_e164.encode("utf-8"), hashlib.sha256).hexdigest()


def twilio_webhook_url(base_url: str, path: str) -> str:
    base = base_url.strip().rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def map_twilio_status(value: str | None) -> str:
    mapping = {
        "queued": "initiated",
        "initiated": "initiated",
        "ringing": "ringing",
        "in-progress": "in_progress",
        "completed": "completed",
        "busy": "busy",
        "no-answer": "no_answer",
        "failed": "failed",
        "canceled": "canceled",
    }
    try:
        return mapping[(value or "").strip().lower()]
    except KeyError as exc:
        raise HTTPException(status_code=422, detail="Unsupported Twilio call status.") from exc


def validate_twilio_request(
    *,
    auth_token: str,
    signature: str | None,
    url: str,
    form: Mapping[str, str],
) -> None:
    if not auth_token or not signature:
        raise HTTPException(status_code=401, detail="Invalid Twilio webhook signature.")
    try:
        from twilio.request_validator import RequestValidator
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise RuntimeError("Twilio server SDK is not installed.") from exc
    validator = RequestValidator(auth_token)
    if not validator.validate(url, form, signature):
        raise HTTPException(status_code=401, detail="Invalid Twilio webhook signature.")
