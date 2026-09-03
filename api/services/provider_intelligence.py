"""Fail-closed provider intelligence primitives.

This module prepares evidence and CRM proposals. It never writes provider or CRM truth.
Network retrieval and document parsing are injected by callers so deterministic workers
or n8n can own those steps without giving an LLM broad execution access.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit


class EvidenceState(StrEnum):
    VERIFIED = "verified"
    STRONG = "strong_source_backed_observation"
    INFERRED = "inferred"
    CONFLICTING = "conflicting"
    WEAK = "weak_unverified"
    HUMAN_REVIEW = "requires_human_review"


RATINGS = {"outstanding", "good", "requires improvement", "inadequate", "not yet inspected"}


def content_sha256(content: bytes | str) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def canonical_url(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    candidate = value.strip()
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", candidate) and "://" not in candidate:
        return None
    if "://" not in candidate:
        candidate = "https://" + candidate
    parts = urlsplit(candidate)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    try:
        port_value = parts.port
    except ValueError:
        return None
    host = parts.hostname.lower()
    port = f":{port_value}" if port_value else ""
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    return urlunsplit((parts.scheme.lower(), host + port, path.rstrip("/") or "/", "", ""))


@dataclass(frozen=True)
class Evidence:
    field: str
    value: Any
    state: EvidenceState
    source_uri: str
    observed_at: str
    source_sha256: str
    source_kind: str
    note: str | None = None


@dataclass(frozen=True)
class Contradiction:
    field: str
    regulator_value: Any
    public_claim_value: Any
    status: EvidenceState = EvidenceState.CONFLICTING
    reason: str = "Public claim differs from the regulator-backed record"


@dataclass(frozen=True)
class ProviderIntelligenceResult:
    location_id: str
    provider_id: str | None
    identity_state: EvidenceState
    evidence: tuple[Evidence, ...]
    contradictions: tuple[Contradiction, ...]
    proposed_updates: Mapping[str, Any]
    proposal_state: EvidenceState
    publish_allowed: bool = False
    review_reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, default=str)


def _normalise_rating(value: object) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in RATINGS else None


def _normalise_integer(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def analyse_provider(
    regulator: Mapping[str, Any],
    public_claims: Mapping[str, Any] | None,
    *,
    regulator_source_uri: str,
    regulator_source_sha256: str,
    observed_at: str | None = None,
) -> ProviderIntelligenceResult:
    """Compare source-backed regulator fields with separately observed public claims."""
    now = observed_at or datetime.now(UTC).isoformat()
    location_id = str(regulator.get("id") or "").strip()
    provider_id = str(regulator.get("provider_id") or "").strip() or None
    identity_ok = bool(location_id and re.fullmatch(r"1-[0-9]+", location_id) and provider_id)
    evidence: list[Evidence] = []
    for field_name in ("name", "overall_rating", "number_of_beds", "website", "inspection_report_url"):
        value = regulator.get(field_name)
        if value not in (None, ""):
            evidence.append(Evidence(
                field=field_name,
                value=value,
                state=EvidenceState.VERIFIED if identity_ok else EvidenceState.STRONG,
                source_uri=regulator_source_uri,
                observed_at=now,
                source_sha256=regulator_source_sha256,
                source_kind="cqc",
            ))

    contradictions: list[Contradiction] = []
    claims = public_claims or {}
    regulator_rating = _normalise_rating(regulator.get("overall_rating"))
    claim_rating = _normalise_rating(claims.get("overall_rating"))
    if regulator_rating and claim_rating and regulator_rating != claim_rating:
        contradictions.append(Contradiction("overall_rating", regulator.get("overall_rating"), claims.get("overall_rating")))
    regulator_beds = _normalise_integer(regulator.get("number_of_beds"))
    claim_beds = _normalise_integer(claims.get("number_of_beds"))
    if regulator_beds is not None and claim_beds is not None and regulator_beds != claim_beds:
        contradictions.append(Contradiction("number_of_beds", regulator_beds, claim_beds))

    proposed: dict[str, Any] = {}
    public_url = canonical_url(claims.get("website"))
    regulator_url = canonical_url(regulator.get("website"))
    if public_url and public_url != regulator_url:
        proposed["website"] = public_url

    review_reasons: list[str] = []
    if not identity_ok:
        review_reasons.append("provider_identity_not_verified")
    if not public_claims:
        review_reasons.append("public_source_not_retrieved")
    if contradictions:
        review_reasons.append("conflicting_evidence")
    if proposed:
        review_reasons.append("crm_update_requires_human_approval")

    if contradictions:
        proposal_state = EvidenceState.CONFLICTING
    elif public_claims and identity_ok:
        proposal_state = EvidenceState.STRONG
    else:
        proposal_state = EvidenceState.HUMAN_REVIEW

    return ProviderIntelligenceResult(
        location_id=location_id,
        provider_id=provider_id,
        identity_state=EvidenceState.VERIFIED if identity_ok else EvidenceState.HUMAN_REVIEW,
        evidence=tuple(evidence),
        contradictions=tuple(contradictions),
        proposed_updates=proposed,
        proposal_state=proposal_state,
        publish_allowed=False,
        review_reasons=tuple(review_reasons),
    )
