"""Fail-closed redaction and advisory DeepSeek evaluation for the local worker."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_UP
from functools import lru_cache
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from api.config import settings
from api.database import get_connection
from api.services.crm_recordings import load_recording_object
from api.services.crm_transcription import transcribe_dual_channel


Disposition = Literal[
    "connected",
    "no_answer",
    "busy",
    "voicemail",
    "wrong_number",
    "callback_requested",
    "gatekeeper",
    "qualified",
    "not_interested",
    "do_not_call",
    "meeting_booked",
    "sale_completed",
]


class CallEvaluation(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    suggested_disposition: Disposition
    overall_qa_score: int = Field(ge=0, le=100)
    customer_sentiment: Literal["positive", "neutral", "negative", "mixed", "unknown"]
    outcome: str = Field(min_length=1, max_length=240)
    strengths: list[str] = Field(default_factory=list, max_length=5)
    coaching_actions: list[str] = Field(default_factory=list, max_length=5)
    compliance_flags: list[str] = Field(default_factory=list, max_length=10)

    model_config = {"extra": "forbid"}

    @field_validator("summary", "outcome")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("strengths", "coaching_actions", "compliance_flags")
    @classmethod
    def validate_list_items(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip()
            if not item or len(item) > 500:
                raise ValueError("Evaluation list items must contain 1 to 500 characters.")
            cleaned.append(item)
        return cleaned


class RedactionError(ValueError):
    """The transcript cannot safely cross the external-provider boundary."""


class ProviderUsagePersistenceError(RuntimeError):
    """Provider may have charged, but its usage evidence was not persisted."""


@dataclass(frozen=True)
class RedactedTranscript:
    text: str
    counts: dict[str, int]
    source_sha256: str
    redacted_sha256: str

    def evidence(self) -> dict[str, Any]:
        return {
            "counts": self.counts,
            "source_sha256": self.source_sha256,
            "redacted_sha256": self.redacted_sha256,
            "policy_version": "caregist-crm-redaction-v1",
        }


@dataclass(frozen=True)
class EvaluationUsage:
    input_tokens: int
    output_tokens: int
    cache_hit_input_tokens: int
    cost_usd: Decimal
    request_id: str
    latency_ms: int


EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<![\w.])(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
POSTCODE_PATTERN = re.compile(
    r"(?i)\b(?:GIR ?0AA|(?:[A-PR-UWYZ][0-9][0-9A-HJKSTUW]?|"
    r"[A-PR-UWYZ][A-HK-Y][0-9][0-9ABEHMNPRV-Y]?) ?[0-9][ABD-HJLNP-UW-Z]{2})\b"
)
NI_PATTERN = re.compile(r"(?i)\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{2}\s?\d{6}\s?[A-D]\b")
IDENTIFIER_PATTERN = re.compile(
    r"(?i)\b(?:nhs|national insurance|ni|account|case|customer|employee|patient|reference)"
    r"\s*(?:number|no\.?|id)?\s*(?:is|:|-)?\s*[A-Z0-9][A-Z0-9 /-]{4,30}\b"
)
HONORIFIC_NAME_PATTERN = re.compile(
    r"(?i)\b(?:mr|mrs|miss|ms|dr|professor)\.?\s+[A-Z][A-Za-z'-]+"
    r"(?:\s+[A-Z][A-Za-z'-]+){0,2}\b"
)
INTRODUCTION_NAME_PATTERN = re.compile(
    r"(?i)\b(?:my name is|this is|speaking with|speak(?:ing)? to|"
    r"ask(?:ing)?(?:\s+for)?|called|contact(?:ed|ing)?|colleague)\s+"
    r"[A-Za-z][A-Za-z'-]{1,50}(?:\s+[A-Za-z][A-Za-z'-]{1,50})?\b"
)
PROPER_NAME_PATTERN = re.compile(r"\b[A-Z][a-z]{1,50}(?:\s+[A-Z][a-z'-]{1,50}){0,3}\b")
ALL_CAPS_NAME_PATTERN = re.compile(
    r"\b(?!AGENT\b|CONTACT\b|CRM\b|TPS\b|CTPS\b|UK\b|AI\b|REDACTED\b|"
    r"NAME\b|EMAIL\b|PHONE\b|POSTCODE\b|IDENTIFIER\b|SENSITIVE\b|INFORMATION\b)"
    r"[A-Z][A-Z'-]{2,50}\b"
)
SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(?:health|medical|diagnos(?:is|ed)|disabilit(?:y|ies)|medication|treatment|"
    r"cancer|chemotherap(?:y|ies)|radiotherap(?:y|ies)|surgery|hospital|doctor|"
    r"anxiety|depression|suicid(?:e|al)|self[- ]?harm|addiction|"
    r"mental health|religion|religious|ethnic(?:ity)?|race|racial|sexual orientation|"
    r"pregnan(?:t|cy)|trade union|criminal conviction|biometric|genetic|bank account|"
    r"credit card|debit card|passport|driving licen[cs]e|date of birth|dob)\b"
)
PLACEHOLDER_PATTERN = re.compile(r"\[REDACTED [A-Z ]+\]")
LOCAL_NER_LABELS = frozenset({"PERSON", "ORG", "GPE", "LOC", "FAC", "NORP", "DATE"})


@lru_cache(maxsize=1)
def _ner_model() -> Any:
    try:
        import spacy

        return spacy.load("en_core_web_sm", disable=("parser", "lemmatizer", "textcat"))
    except (ImportError, OSError) as exc:
        raise RedactionError(
            "The approved local redaction model is unavailable; external AI is blocked."
        ) from exc


def _case_normalized(text: str) -> str:
    # Whisper casing is not a privacy boundary. Capitalising word initials is
    # length preserving, allowing a second NER pass to find lowercase names
    # while mapping entity offsets back to the original text.
    return re.sub(
        r"(?<![A-Za-z])[a-z][A-Za-z'-]*",
        lambda match: match.group(0)[0].upper() + match.group(0)[1:],
        text,
    )


def _local_entity_spans(text: str, *, required: bool) -> list[tuple[int, int]]:
    if not required:
        return []
    model = _ner_model()
    analysis = PLACEHOLDER_PATTERN.sub(lambda match: " " * len(match.group(0)), text)
    spans: set[tuple[int, int]] = set()
    for candidate in (analysis, _case_normalized(analysis)):
        document = model(candidate)
        for entity in document.ents:
            if entity.label_ in LOCAL_NER_LABELS:
                spans.add((entity.start_char, entity.end_char))
        # Entity labels are statistical and sometimes misclassify uncommon
        # names (for example as DATE) or omit a surname. Proper-noun tokens are
        # therefore independently sensitive and adjacent alphabetic tokens are
        # included to avoid leaving name fragments.
        for token in document:
            if token.pos_ == "PROPN":
                start, end = token.idx, token.idx + len(token.text)
                next_token = document[token.i + 1] if token.i + 1 < len(document) else None
                if next_token is not None and next_token.is_alpha:
                    end = next_token.idx + len(next_token.text)
                spans.add((start, end))
    # Merge overlapping detections so replacements cannot leave fragments.
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _redact_local_entities(text: str, counts: dict[str, int], *, required: bool) -> str:
    spans = _local_entity_spans(text, required=required)
    for start, end in reversed(spans):
        text = text[:start] + "[REDACTED NAME]" + text[end:]
    if spans:
        counts["local_ner_entity"] = counts.get("local_ner_entity", 0) + len(spans)
    return text


def provider_name(base_url: str) -> str:
    return "deepseek" if "deepseek" in base_url.lower() else "openai_compatible"


def parse_evaluation_json(content: str) -> CallEvaluation:
    candidate = content.strip()
    if not candidate:
        raise ValueError("Evaluation provider returned no content.")
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if candidate.startswith("json"):
            candidate = candidate[4:].lstrip()
    payload = json.loads(candidate)
    return CallEvaluation.model_validate(payload)


def _replace_pattern(
    text: str,
    pattern: re.Pattern[str],
    replacement: str,
    counts: dict[str, int],
    category: str,
) -> str:
    text, count = pattern.subn(replacement, text)
    counts[category] = counts.get(category, 0) + count
    return text


def redact_transcript(
    transcript: str, *, known_entities: tuple[str, ...] = (), require_local_ner: bool = False
) -> RedactedTranscript:
    """Remove required personal/sensitive data and prove no known pattern remains."""
    if not transcript.strip():
        raise RedactionError("An empty transcript cannot be sent externally.")
    if len(transcript) > 120_000:
        raise RedactionError("Transcript exceeds the approved external-processing limit.")

    source_sha256 = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    counts: dict[str, int] = {}
    redacted = transcript
    # Structured values are removed before names so an email local-part such as
    # jane.smith cannot be partially obscured while leaving its domain visible.
    for pattern, replacement, category in (
        (EMAIL_PATTERN, "[REDACTED EMAIL]", "email"),
        (PHONE_PATTERN, "[REDACTED PHONE]", "phone"),
        (POSTCODE_PATTERN, "[REDACTED POSTCODE]", "postcode"),
        (NI_PATTERN, "[REDACTED IDENTIFIER]", "national_insurance"),
        (IDENTIFIER_PATTERN, "[REDACTED IDENTIFIER]", "identifier"),
    ):
        redacted = _replace_pattern(redacted, pattern, replacement, counts, category)

    for entity in sorted({item.strip() for item in known_entities if item.strip()}, key=len, reverse=True):
        # Full CRM-known values and their person-name components are removed. A
        # two-character minimum avoids destroying ordinary one-letter speech.
        candidates = {entity}
        if " " in entity:
            candidates.update(part for part in re.split(r"\s+", entity) if len(part) >= 2)
        for candidate in sorted(candidates, key=len, reverse=True):
            pattern = re.compile(rf"(?i)(?<!\w){re.escape(candidate)}(?!\w)")
            redacted = _replace_pattern(
                redacted, pattern, "[REDACTED NAME]", counts, "known_name"
            )

    for pattern, replacement, category in (
        (HONORIFIC_NAME_PATTERN, "[REDACTED NAME]", "contextual_name"),
        (INTRODUCTION_NAME_PATTERN, "[REDACTED NAME]", "contextual_name"),
    ):
        redacted = _replace_pattern(redacted, pattern, replacement, counts, category)

    safe_lines: list[str] = []
    for line in redacted.splitlines():
        if SENSITIVE_PATTERN.search(line):
            prefix = line.split(":", 1)[0] + ":" if ":" in line else ""
            safe_lines.append(f"{prefix} [REDACTED SENSITIVE INFORMATION]")
            counts["sensitive_line"] = counts.get("sensitive_line", 0) + 1
        else:
            if ":" in line:
                prefix, content = line.split(":", 1)
                content = _redact_local_entities(
                    content, counts, required=require_local_ner
                )
                content = _replace_pattern(
                    content, PROPER_NAME_PATTERN, "[REDACTED NAME]", counts, "possible_name"
                )
                content = _replace_pattern(
                    content, ALL_CAPS_NAME_PATTERN, "[REDACTED NAME]", counts, "possible_name"
                )
                safe_lines.append(prefix + ":" + content)
            else:
                line = _redact_local_entities(line, counts, required=require_local_ner)
                line = _replace_pattern(
                    line, PROPER_NAME_PATTERN, "[REDACTED NAME]", counts, "possible_name"
                )
                safe_lines.append(
                    _replace_pattern(
                        line, ALL_CAPS_NAME_PATTERN, "[REDACTED NAME]", counts, "possible_name"
                    )
                )
    redacted = "\n".join(safe_lines)

    residual_patterns = (
        EMAIL_PATTERN,
        PHONE_PATTERN,
        POSTCODE_PATTERN,
        NI_PATTERN,
        IDENTIFIER_PATTERN,
        HONORIFIC_NAME_PATTERN,
        INTRODUCTION_NAME_PATTERN,
        SENSITIVE_PATTERN,
    )
    if any(pattern.search(redacted) for pattern in residual_patterns):
        raise RedactionError("Transcript redaction could not be proven complete.")
    for line in redacted.splitlines():
        content = line.split(":", 1)[1] if ":" in line else line
        if _local_entity_spans(content, required=require_local_ner):
            raise RedactionError("A local NER entity remains after redaction.")
        if PROPER_NAME_PATTERN.search(content):
            raise RedactionError("A possible personal name remains after redaction.")
    for entity in known_entities:
        if entity.strip() and re.search(rf"(?i)(?<!\w){re.escape(entity.strip())}(?!\w)", redacted):
            raise RedactionError("A known CRM entity remains after redaction.")
    if not redacted.strip():
        raise RedactionError("Transcript contains no reviewable content after redaction.")

    return RedactedTranscript(
        text=redacted,
        counts=counts,
        source_sha256=source_sha256,
        redacted_sha256=hashlib.sha256(redacted.encode("utf-8")).hexdigest(),
    )


def pseudonymous_user_id(call_session_id: Any) -> str:
    key = settings.crm_ai_pseudonym_key.encode("utf-8")
    if len(key) < 32:
        raise RuntimeError("CRM AI pseudonym key is not configured safely.")
    return hmac.new(key, str(call_session_id).encode("utf-8"), hashlib.sha256).hexdigest()


def calculate_cost_usd(
    *, input_tokens: int, output_tokens: int, cache_hit_input_tokens: int = 0
) -> Decimal:
    cached = min(max(cache_hit_input_tokens, 0), max(input_tokens, 0))
    uncached = max(input_tokens, 0) - cached
    cost = (
        Decimal(uncached) * settings.crm_ai_input_price_usd_per_million
        + Decimal(cached) * settings.crm_ai_cache_hit_price_usd_per_million
        + Decimal(max(output_tokens, 0)) * settings.crm_ai_output_price_usd_per_million
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.00000001"), rounding=ROUND_UP)


def maximum_request_cost_usd() -> Decimal:
    # A 120,000-code-point transcript occupies at most 480,000 UTF-8 bytes. A
    # byte-level tokenizer cannot emit more than one non-empty token per byte;
    # the remaining 20,000 tokens cover the fixed prompt and message framing.
    # This avoids relying on normal-language characters-per-token estimates for
    # adversarial Unicode while retaining a deterministic hard-cap reservation.
    return calculate_cost_usd(input_tokens=500_000, output_tokens=1_200)


MAX_EVALUATION_ATTEMPTS = 3
PROVIDER_EXPIRY_HEADROOM_MINUTES = 7
CLAIM_EXPIRY_HEADROOM_MINUTES = 25


async def evaluate_transcript(
    redacted: RedactedTranscript, *, user_id: str, intelligence_id: Any | None = None
) -> tuple[CallEvaluation, EvaluationUsage]:
    """Send only a redacted transcript and retry malformed provider output."""
    system_prompt = (
        "You evaluate UK B2B sales calls for coaching. Return JSON only with exactly: "
        "summary, suggested_disposition, overall_qa_score, customer_sentiment, outcome, "
        "strengths, coaching_actions, compliance_flags. suggested_disposition must be one of "
        "connected, no_answer, busy, voicemail, wrong_number, callback_requested, gatekeeper, "
        "qualified, not_interested, do_not_call, meeting_booked, sale_completed. "
        "Use only spoken words for sentiment. Do not infer protected traits, health, emotion, "
        "lawfulness or employee intent. Flag uncertainty. Output is advisory and cannot alter CRM state."
    )
    payload: dict[str, Any] = {
        "model": settings.crm_ai_model,
        "temperature": 0,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "user_id": user_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": redacted.text},
        ],
    }
    url = settings.crm_ai_base_url.rstrip("/") + "/chat/completions"
    last_error: Exception | None = None
    for attempt in range(MAX_EVALUATION_ATTEMPTS):
        started = time.monotonic()
        response_payload: dict[str, Any] | None = None
        attempt_recorded = False
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {settings.crm_ai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            response_payload = response.json()
            usage_payload = response_payload.get("usage") or {}
            details = usage_payload.get("prompt_tokens_details") or {}
            input_tokens = int(usage_payload.get("prompt_tokens") or 0)
            output_tokens = int(usage_payload.get("completion_tokens") or 0)
            cached_tokens = int(details.get("cached_tokens") or 0)
            attempt_cost = calculate_cost_usd(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_hit_input_tokens=cached_tokens,
            )
            choice = response_payload["choices"][0]
            if choice.get("finish_reason") not in {"stop", None}:
                raise ValueError("Evaluation response was truncated.")
            evaluation = parse_evaluation_json(choice["message"]["content"])
            if input_tokens <= 0 or output_tokens <= 0:
                raise ValueError("Evaluation response omitted token usage.")
            if intelligence_id is not None:
                try:
                    await _record_usage_attempt(
                        intelligence_id=intelligence_id,
                        request_id=str(response_payload.get("id") or "")[:255],
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached_tokens=cached_tokens,
                        cost_usd=attempt_cost,
                        schema_valid=True,
                    )
                except Exception as exc:
                    raise ProviderUsagePersistenceError(
                        "Provider usage could not be persisted."
                    ) from exc
                attempt_recorded = True
            return evaluation, EvaluationUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_hit_input_tokens=cached_tokens,
                cost_usd=attempt_cost,
                request_id=str(response_payload.get("id") or "")[:255],
                latency_ms=max(0, int((time.monotonic() - started) * 1000)),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            if intelligence_id is not None and not attempt_recorded:
                usage_payload = (response_payload or {}).get("usage") or {}
                details = usage_payload.get("prompt_tokens_details") or {}
                input_tokens = int(usage_payload.get("prompt_tokens") or 0)
                output_tokens = int(usage_payload.get("completion_tokens") or 0)
                cached_tokens = int(details.get("cached_tokens") or 0)
                # A timeout or provider response without usage may still have
                # incurred cost. Charge the maximum; ambiguous billing must not
                # weaken the hard cap.
                usage_known = bool(input_tokens or output_tokens)
                try:
                    await _record_usage_attempt(
                        intelligence_id=intelligence_id,
                        request_id=str((response_payload or {}).get("id") or "")[:255],
                        input_tokens=input_tokens if usage_known else 500_000,
                        output_tokens=output_tokens if usage_known else 1_200,
                        cached_tokens=cached_tokens if usage_known else 0,
                        cost_usd=(
                            calculate_cost_usd(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                cache_hit_input_tokens=cached_tokens,
                            )
                            if usage_known else maximum_request_cost_usd()
                        ),
                        schema_valid=False,
                    )
                except Exception as persistence_exc:
                    raise ProviderUsagePersistenceError(
                        "Ambiguous provider usage could not be persisted."
                    ) from persistence_exc
            if attempt < MAX_EVALUATION_ATTEMPTS - 1:
                await asyncio.sleep(0.25 * (2**attempt))
    raise RuntimeError("DeepSeek returned no valid schema-bound evaluation after three attempts.") from last_error


async def _record_usage_attempt(
    *, intelligence_id: Any, request_id: str, input_tokens: int,
    output_tokens: int, cached_tokens: int, cost_usd: Decimal, schema_valid: bool,
) -> None:
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_ai', true)")
            await conn.execute(
                """
                INSERT INTO crm_ai_usage_attempts (
                  intelligence_id, request_id, input_tokens, output_tokens,
                  cache_hit_input_tokens, cost_usd, schema_valid
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                intelligence_id, request_id or None, input_tokens, output_tokens,
                cached_tokens, cost_usd, schema_valid,
            )
            # The usage row makes this attempt's charge durable. Release only
            # that attempt's pessimistic hold; any attempt whose ledger write
            # fails keeps its reservation and therefore fails closed.
            await conn.execute(
                """
                UPDATE crm_call_intelligence
                SET reserved_cost_usd = GREATEST(reserved_cost_usd - $2, 0),
                    updated_at = NOW()
                WHERE id = $1 AND status = 'processing'
                """,
                intelligence_id,
                maximum_request_cost_usd(),
            )


async def _claim_job() -> dict[str, Any] | None:
    reservation = maximum_request_cost_usd() * MAX_EVALUATION_ATTEMPTS
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_ai', true)")
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext('caregist.crm_ai.monthly_budget'))")
            row = await conn.fetchrow(
                """
                SELECT intelligence.id, intelligence.organization_id,
                       intelligence.call_session_id, intelligence.attempts,
                       CASE
                         WHEN intelligence.status = 'processing'
                           OR intelligence.updated_at >= date_trunc('month', NOW())
                         THEN intelligence.reserved_cost_usd
                         ELSE 0
                       END AS existing_reservation,
                       recording.object_key,
                       contact.first_name, contact.last_name, contact.company_name,
                       agent.name AS agent_name
                FROM crm_call_intelligence intelligence
                JOIN crm_recordings recording ON recording.id = intelligence.recording_id
                JOIN crm_call_sessions call ON call.id = intelligence.call_session_id
                JOIN crm_contacts contact ON contact.id = call.contact_id
                JOIN users agent ON agent.id = call.agent_user_id
                WHERE (
                    intelligence.status IN ('pending', 'failed')
                    OR (
                      intelligence.status = 'processing'
                      AND intelligence.processing_started_at < NOW() - INTERVAL '15 minutes'
                    )
                  )
                  AND intelligence.attempts < 3
                  AND recording.status = 'ready'
                  AND recording.expires_at > NOW() + make_interval(mins => $1)
                ORDER BY intelligence.created_at
                FOR UPDATE OF intelligence SKIP LOCKED
                LIMIT 1
                """,
                CLAIM_EXPIRY_HEADROOM_MINUTES,
            )
            if not row:
                return None
            month_spend = await conn.fetchval(
                """
                SELECT
                  COALESCE((SELECT SUM(cost_usd) FROM crm_ai_usage_attempts
                            WHERE incurred_at >= date_trunc('month', NOW())), 0)
                  + COALESCE((SELECT SUM(reserved_cost_usd) FROM crm_call_intelligence
                              WHERE status = 'processing'
                                 OR (status = 'failed'
                                     AND updated_at >= date_trunc('month', NOW()))
                                 OR (status IN ('completed', 'purged')
                                     AND reserved_cost_usd > 0
                                     AND processed_at >= date_trunc('month', NOW()))), 0)
                """
            )
            if Decimal(str(month_spend)) + reservation > settings.crm_ai_monthly_cap_usd:
                await conn.execute(
                    """
                    UPDATE crm_call_intelligence
                    SET status = 'failed', attempts = 3, error_code = 'monthly_cap_exceeded',
                        reserved_cost_usd = $2, processing_started_at = NULL, updated_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                    row["existing_reservation"],
                )
                return None
            claimed = await conn.fetchrow(
                """
                UPDATE crm_call_intelligence SET
                  status = 'processing', attempts = attempts + 1,
                  reserved_cost_usd = $2 + $3, processing_started_at = NOW(),
                  error_code = NULL, updated_at = NOW()
                WHERE id = $1
                RETURNING attempts
                """,
                row["id"],
                reservation,
                row["existing_reservation"],
            )
    result = dict(row)
    result["attempts"] = claimed["attempts"]
    return result


async def record_worker_heartbeat(status: str, *, metadata: dict[str, Any] | None = None) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO crm_worker_heartbeats (worker_name, status, last_seen_at, metadata)
            VALUES ('crm_ai', $1, NOW(), $2::jsonb)
            ON CONFLICT (worker_name) DO UPDATE SET
              status = EXCLUDED.status, last_seen_at = EXCLUDED.last_seen_at,
              metadata = EXCLUDED.metadata
            """,
            status,
            json.dumps(metadata or {}),
        )


async def _job_is_current(job: dict[str, Any]) -> bool:
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_ai', true)")
            return bool(
                await conn.fetchval(
                    """
                    SELECT 1
                    FROM crm_call_intelligence intelligence
                    JOIN crm_recordings recording ON recording.id = intelligence.recording_id
                    WHERE intelligence.id = $1 AND intelligence.status = 'processing'
                      AND intelligence.attempts = $2 AND recording.status = 'ready'
                      AND recording.expires_at > NOW() + make_interval(mins => $3)
                    """,
                    job["id"], job["attempts"], PROVIDER_EXPIRY_HEADROOM_MINUTES,
                )
            )


async def process_ai_jobs(*, limit: int = 2) -> dict[str, int]:
    if not settings.crm_ai_enabled:
        return {"processed": 0, "failed": 0}
    processed = failed = 0
    for _ in range(max(0, min(limit, 10))):
        job = await _claim_job()
        if not job:
            break
        try:
            audio = await load_recording_object(job["object_key"])
            transcript = await transcribe_dual_channel(audio)
            known_entities = tuple(
                str(job.get(name) or "").strip()
                for name in ("first_name", "last_name", "company_name", "agent_name")
                if str(job.get(name) or "").strip()
            )
            redacted = redact_transcript(
                transcript, known_entities=known_entities, require_local_ner=True
            )
            external_user_id = pseudonymous_user_id(job["call_session_id"])
            if not await _job_is_current(job):
                raise RuntimeError("AI job expired before external evaluation.")
            evaluation, usage = await evaluate_transcript(
                redacted, user_id=external_user_id, intelligence_id=job["id"]
            )
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('caregist.worker', 'crm_ai', true)")
                    updated = await conn.fetchval(
                        """
                        UPDATE crm_call_intelligence SET
                          status = 'completed', transcript = $2, summary = $3,
                          evaluation = $4::jsonb, redaction_summary = $5::jsonb,
                          transcription_provider = 'local_faster_whisper',
                          transcription_model = $6,
                          evaluation_provider = $7, evaluation_model = $8,
                          external_user_id = $9, external_request_id = $10,
                          input_tokens = $11, output_tokens = $12,
                          cache_hit_input_tokens = $13, actual_cost_usd = $14,
                          reserved_cost_usd = $17, evaluation_latency_ms = $15,
                          processed_at = NOW(), processing_started_at = NULL, updated_at = NOW()
                        WHERE id = $1 AND status = 'processing' AND attempts = $16
                          AND EXISTS (
                            SELECT 1 FROM crm_recordings recording
                            WHERE recording.id = crm_call_intelligence.recording_id
                              AND recording.status = 'ready' AND recording.expires_at > NOW()
                          )
                        RETURNING id
                        """,
                        job["id"],
                        transcript,
                        evaluation.summary,
                        json.dumps(evaluation.model_dump()),
                        json.dumps(redacted.evidence()),
                        settings.crm_transcription_model,
                        provider_name(settings.crm_ai_base_url),
                        settings.crm_ai_model,
                        external_user_id,
                        usage.request_id or None,
                        usage.input_tokens,
                        usage.output_tokens,
                        usage.cache_hit_input_tokens,
                        usage.cost_usd,
                        usage.latency_ms,
                        job["attempts"],
                        job["existing_reservation"],
                    )
                    if not updated:
                        raise RuntimeError("AI job lease expired or retention already purged the call.")
                    await conn.execute(
                        """
                        INSERT INTO crm_activities (
                          organization_id, contact_id, activity_type, metadata
                        )
                        SELECT $1, call.contact_id, 'ai_evaluation_completed',
                          jsonb_build_object('call_session_id', $2::uuid, 'score', $3::int)
                        FROM crm_call_sessions call WHERE call.id = $2
                        """,
                        job["organization_id"],
                        job["call_session_id"],
                        evaluation.overall_qa_score,
                    )
            processed += 1
        except Exception as exc:
            retained_reservation = Decimal(str(job["existing_reservation"]))
            if isinstance(exc, ProviderUsagePersistenceError):
                retained_reservation += maximum_request_cost_usd()
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('caregist.worker', 'crm_ai', true)")
                    await conn.execute(
                        """
                        UPDATE crm_call_intelligence
                        SET status = 'failed', error_code = $2,
                            reserved_cost_usd = $4,
                            processing_started_at = NULL, updated_at = NOW()
                        WHERE id = $1 AND status = 'processing' AND attempts = $3
                        """,
                        job["id"],
                        type(exc).__name__[:80],
                        job["attempts"],
                        retained_reservation,
                    )
            failed += 1
    return {"processed": processed, "failed": failed}
