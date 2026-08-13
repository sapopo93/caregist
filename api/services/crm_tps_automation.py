"""Durable, fail-closed CQC-to-TPSCheck-to-CRM automation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import httpx
import phonenumbers

from api.config import settings
from api.database import get_connection
from api.services.crm_calling import hash_screening_number, normalize_e164
from api.services.new_registration_feed import FeedFilters, coerce_json_object


logger = logging.getLogger("caregist.crm_tps_automation")
WORKER_NAME = "crm_tps"
SOURCE = "approved_provider"
API_VERSION = "2"
GLOBAL_LOCK_KEY = 0x43545053  # "CTPS"
MAX_ATTEMPTS = 5
LEASE_MINUTES = 5
FRESHNESS_DAYS = 27
MAX_RUN_LIMIT = 50
REQUEST_SPACING_SECONDS = 1.05
RUN_BUDGET_SECONDS = 52.0
MAX_PROVIDER_RESPONSE_BYTES = 256 * 1024


@dataclass(frozen=True)
class TpsCheckResult:
    phone_e164: str
    status: str
    valid: bool
    tps: bool
    ctps: bool
    screened_at: datetime
    response: dict[str, Any]
    response_sha256: str


class TpsCheckError(RuntimeError):
    def __init__(self, message: str, *, http_status: int | None = None, retryable: bool = True):
        super().__init__(message)
        self.http_status = http_status
        self.retryable = retryable


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_email(value: object) -> str | None:
    email = str(value or "").strip().lower()
    if not email or len(email) > 320 or "@" not in email:
        return None
    return email


def normalize_uk_provider_phone(value: object) -> str | None:
    """Convert trusted CQC national/international phone text to UK E.164."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, "GB")
    except phonenumbers.NumberParseException:
        return None
    if parsed.country_code != 44 or not phonenumbers.is_possible_number(parsed):
        return None
    normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return normalized if normalize_e164(normalized) else None


def parse_tpscheck_result(payload: object, expected_phone: str) -> TpsCheckResult:
    """Validate the provider response; ambiguity never becomes a clear result."""
    if not isinstance(payload, dict):
        raise TpsCheckError("TPSCheck returned a non-object response.", retryable=False)
    for field in ("valid", "tps", "ctps"):
        if not isinstance(payload.get(field), bool):
            raise TpsCheckError(f"TPSCheck response omitted boolean {field}.", retryable=False)
    returned_phone = normalize_e164(payload.get("e164") or expected_phone)
    if returned_phone != expected_phone:
        raise TpsCheckError("TPSCheck returned a different phone number.", retryable=False)
    valid = payload["valid"]
    tps = payload["tps"]
    ctps = payload["ctps"]
    status = "invalid" if not valid else "tps" if tps else "ctps" if ctps else "clear"
    return TpsCheckResult(
        phone_e164=expected_phone,
        status=status,
        valid=valid,
        tps=tps,
        ctps=ctps,
        screened_at=datetime.now(UTC),
        response=payload,
        response_sha256=_canonical_sha256(payload),
    )


async def _worker_context(conn) -> None:
    await conn.execute("SELECT set_config('caregist.user_id', '', true)")
    await conn.execute("SELECT set_config('caregist.worker', $1, true)", WORKER_NAME)


async def _fetch_credits(client: httpx.AsyncClient) -> dict[str, Any]:
    try:
        response = await client.get(
            f"{settings.crm_tpscheck_base_url}/credits",
            headers={"Authorization": f"Token {settings.crm_tpscheck_api_key}"},
        )
    except httpx.HTTPError as exc:
        raise TpsCheckError("TPSCheck credits request failed before a valid response.") from exc
    if response.status_code != 200:
        raise TpsCheckError(
            f"TPSCheck credits request failed with HTTP {response.status_code}.",
            http_status=response.status_code,
            retryable=response.status_code >= 500 or response.status_code == 429,
        )
    if len(response.content) > MAX_PROVIDER_RESPONSE_BYTES:
        raise TpsCheckError("TPSCheck credits response exceeded the size limit.", retryable=False)
    try:
        payload = response.json()
    except ValueError as exc:
        raise TpsCheckError("TPSCheck credits response was malformed JSON.", retryable=False) from exc
    required = ("requests_used", "requests_remaining", "monthly_limit", "plan", "reset_date")
    if not isinstance(payload, dict) or any(field not in payload for field in required):
        raise TpsCheckError("TPSCheck credits response is incomplete.", retryable=False)
    if not all(isinstance(payload[field], int) for field in required[:3]):
        raise TpsCheckError("TPSCheck credits counters are invalid.", retryable=False)
    return payload


async def _screen_phone(client: httpx.AsyncClient, phone_e164: str) -> tuple[TpsCheckResult, int]:
    try:
        response = await client.post(
            f"{settings.crm_tpscheck_base_url}/check",
            params={"version": API_VERSION},
            headers={
                "Authorization": f"Token {settings.crm_tpscheck_api_key}",
                "Content-Type": "application/json",
            },
            json={"phone": phone_e164},
        )
    except httpx.HTTPError as exc:
        raise TpsCheckError("TPSCheck request failed before a valid response.") from exc
    if response.status_code != 200:
        raise TpsCheckError(
            f"TPSCheck check failed with HTTP {response.status_code}.",
            http_status=response.status_code,
            retryable=response.status_code >= 500 or response.status_code == 429,
        )
    if len(response.content) > MAX_PROVIDER_RESPONSE_BYTES:
        raise TpsCheckError("TPSCheck response exceeded the size limit.", retryable=False)
    try:
        payload = response.json()
    except ValueError as exc:
        raise TpsCheckError("TPSCheck returned malformed JSON.", retryable=False) from exc
    return parse_tpscheck_result(payload, phone_e164), response.status_code


def _feed_filters(automation: dict[str, Any]) -> FeedFilters:
    raw = coerce_json_object(automation.get("filter_config"))
    configured_from = raw.get("from_date")
    from_date = automation["registered_from"].isoformat()
    if isinstance(configured_from, str) and configured_from > from_date:
        from_date = configured_from
    return FeedFilters(
        q=raw.get("q"),
        region=raw.get("region"),
        local_authority=raw.get("local_authority"),
        service_type=raw.get("service_type"),
        provider_type=raw.get("provider_type"),
        postcode_prefix=raw.get("postcode_prefix"),
        from_date=from_date,
        to_date=raw.get("to_date"),
    )


def _candidate_query(automation: dict[str, Any], limit: int) -> tuple[str, list[Any]]:
    """Use exactly the feed's filter semantics while excluding already queued providers."""
    filters = _feed_filters(automation)
    args: list[Any] = [automation["organization_id"], date.fromisoformat(filters.from_date or "")]
    clauses = [
        "event.event_type = 'new_registration'",
        "event.effective_date >= $2",
        "cp.phone IS NOT NULL",
        "BTRIM(cp.phone) <> ''",
        "NOT EXISTS (SELECT 1 FROM crm_tps_screening_jobs job "
        "WHERE job.organization_id = $1 AND job.provider_id = cp.id)",
    ]

    def add(clause: str, value: object) -> None:
        args.append(value)
        clauses.append(clause.format(index=len(args)))

    if filters.q:
        add(
            "(cp.name ILIKE ${index} OR cp.town ILIKE ${index} "
            "OR cp.local_authority ILIKE ${index})",
            f"%{filters.q}%",
        )
    if filters.region:
        add("cp.region = ${index}", filters.region)
    if filters.local_authority:
        add("cp.local_authority = ${index}", filters.local_authority)
    if filters.service_type:
        add("cp.service_types ILIKE ${index}", f"%{filters.service_type}%")
    if filters.provider_type:
        add("cp.type = ${index}", filters.provider_type)
    if filters.postcode_prefix:
        add(
            "replace(cp.postcode, ' ', '') ILIKE ${index}",
            f"{filters.postcode_prefix.replace(' ', '').upper()}%",
        )
    if filters.to_date:
        add("event.effective_date <= ${index}", date.fromisoformat(filters.to_date))
    args.append(limit)
    query = f"""
        SELECT DISTINCT ON (cp.id) cp.id AS provider_id, cp.phone
        FROM trusted_event_ledger event
        JOIN care_providers cp ON cp.id = COALESCE(event.location_id, event.entity_id)
        WHERE {' AND '.join(clauses)}
        ORDER BY cp.id, event.effective_date, event.observed_at
        LIMIT ${len(args)}
    """
    return query, args


async def seed_tps_jobs(*, per_organization_limit: int = 250) -> int:
    """Seed new-registration jobs and requeue results approaching 28 days old."""
    seeded = 0
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            automation_settings = await conn.fetch(
                """
                SELECT organization_id, registered_from, filter_config
                FROM crm_tps_automation_settings
                WHERE enabled = TRUE
                ORDER BY created_at
                """
            )
            for automation in automation_settings:
                stale = await conn.fetch(
                    """
                    SELECT job.id, cp.phone
                    FROM crm_tps_screening_jobs job
                    JOIN care_providers cp ON cp.id = job.provider_id
                    WHERE job.organization_id = $1
                      AND job.status = 'completed'
                      AND job.screened_at < NOW() - ($2::int * INTERVAL '1 day')
                    ORDER BY job.screened_at
                    LIMIT $3
                    FOR UPDATE OF job SKIP LOCKED
                    """,
                    automation["organization_id"],
                    FRESHNESS_DAYS,
                    per_organization_limit,
                )
                for row in stale:
                    phone = normalize_uk_provider_phone(row["phone"])
                    if not phone or not phone.startswith("+44"):
                        await conn.execute(
                            """
                            UPDATE crm_tps_screening_jobs
                            SET status = 'review_required', last_error = 'Provider phone is no longer a valid UK number',
                                lease_token = NULL, lease_expires_at = NULL, updated_at = NOW()
                            WHERE id = $1
                            """,
                            row["id"],
                        )
                        continue
                    await conn.execute(
                        """
                        UPDATE crm_tps_screening_jobs
                        SET phone_e164 = $2, status = 'queued', screening_status = NULL,
                            attempts = 0, next_attempt_at = NOW(), lease_token = NULL,
                            lease_expires_at = NULL, screened_at = NULL,
                            provider_reference = NULL, result_sha256 = NULL,
                            result_payload = NULL, last_http_status = NULL,
                            last_error = NULL, updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                        phone,
                    )
                    seeded += 1

                candidate_query, candidate_args = _candidate_query(
                    dict(automation), per_organization_limit
                )
                feed_rows = await conn.fetch(candidate_query, *candidate_args)
                rows = []
                for candidate in feed_rows:
                    phone = normalize_uk_provider_phone(candidate["phone"])
                    rows.append(
                        (
                            automation["organization_id"],
                            candidate["provider_id"],
                            phone,
                            "queued" if phone else "review_required",
                            None if phone else "Provider phone is not a possible UK number",
                        )
                    )
                if rows:
                    await conn.executemany(
                        """
                        INSERT INTO crm_tps_screening_jobs (
                          organization_id, provider_id, phone_e164, status, last_error
                        ) VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (organization_id, provider_id) DO NOTHING
                        """,
                        rows,
                    )
                    seeded += len(rows)
    return seeded


async def _claim_job() -> dict[str, Any] | None:
    lease_token = uuid4()
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            await conn.execute(
                """
                UPDATE crm_tps_screening_jobs
                SET status = 'retryable', lease_token = NULL, lease_expires_at = NULL,
                    next_attempt_at = NOW(), last_error = 'Worker lease expired', updated_at = NOW()
                WHERE status = 'processing' AND lease_expires_at < NOW()
                """
            )
            row = await conn.fetchrow(
                """
                SELECT job.id, job.organization_id, job.provider_id, job.phone_e164,
                       job.attempts, automation.assigned_user_id,
                       automation.configured_by_user_id, automation.max_monthly_checks
                FROM crm_tps_screening_jobs job
                JOIN crm_tps_automation_settings automation
                  ON automation.organization_id = job.organization_id
                WHERE automation.enabled = TRUE
                  AND job.status IN ('queued', 'retryable')
                  AND job.next_attempt_at <= NOW()
                  AND job.attempts < $1
                  AND (
                    SELECT COUNT(*) FROM crm_tps_usage_attempts monthly
                    WHERE monthly.organization_id = job.organization_id
                      AND monthly.request_started_at >= date_trunc('month', NOW())
                  ) < automation.max_monthly_checks
                ORDER BY job.next_attempt_at, job.created_at
                LIMIT 1
                FOR UPDATE OF job SKIP LOCKED
                """,
                MAX_ATTEMPTS,
            )
            if not row:
                return None
            claimed = await conn.fetchrow(
                """
                UPDATE crm_tps_screening_jobs
                SET status = 'processing', attempts = attempts + 1, lease_token = $2,
                    lease_expires_at = NOW() + ($3::int * INTERVAL '1 minute'),
                    last_error = NULL, updated_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                row["id"],
                lease_token,
                LEASE_MINUTES,
            )
            return {
                **dict(row),
                **dict(claimed),
                "lease_token": lease_token,
            }


async def _configured_run_limit(requested_limit: int) -> int:
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            configured = await conn.fetchval(
                "SELECT MIN(per_run_limit) FROM crm_tps_automation_settings WHERE enabled = TRUE"
            )
    return min(requested_limit, int(configured or requested_limit))


async def _record_run_error(message: str) -> None:
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            await conn.execute(
                """
                UPDATE crm_tps_automation_settings SET
                  last_run_at = NOW(), last_error = $1, updated_at = NOW()
                WHERE enabled = TRUE
                """,
                message[:500],
            )


async def _mark_failure(job: dict[str, Any], error: TpsCheckError) -> None:
    terminal = not error.retryable or int(job["attempts"]) >= MAX_ATTEMPTS
    status = "review_required" if terminal else "retryable"
    backoff_minutes = min(30, 2 ** max(0, int(job["attempts"])))
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            await conn.execute(
                """
                UPDATE crm_tps_screening_jobs
                SET status = $3, lease_token = NULL, lease_expires_at = NULL,
                    next_attempt_at = NOW() + ($4::int * INTERVAL '1 minute'),
                    last_http_status = $5, last_error = $6, updated_at = NOW()
                WHERE id = $1 AND lease_token = $2 AND status = 'processing'
                """,
                job["id"],
                job["lease_token"],
                status,
                backoff_minutes,
                error.http_status,
                str(error)[:500],
            )


async def _reserve_usage_attempt(job: dict[str, Any]):
    """Count a provider request before sending it so ambiguous charges remain capped."""
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            attempt_id = await conn.fetchval(
                """
                INSERT INTO crm_tps_usage_attempts (organization_id, job_id)
                SELECT organization_id, id FROM crm_tps_screening_jobs
                WHERE id = $1 AND lease_token = $2 AND status = 'processing'
                RETURNING id
                """,
                job["id"],
                job["lease_token"],
            )
            if not attempt_id:
                raise TpsCheckError("TPS job lease expired before its request was reserved.", retryable=False)
            return attempt_id


async def _record_usage_ambiguous(
    job: dict[str, Any], attempt_id, http_status: int | None
) -> None:
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            await conn.execute(
                """
                UPDATE crm_tps_usage_attempts
                SET outcome = 'ambiguous', response_received_at = NOW(), http_status = $3
                WHERE id = $1 AND organization_id = $2 AND outcome = 'started'
                """,
                attempt_id,
                job["organization_id"],
                http_status,
            )


async def _record_provider_result(
    job: dict[str, Any], result: TpsCheckResult, http_status: int, usage_attempt_id=None
) -> None:
    """Durably retain the billed provider result before CRM materialisation."""
    reference = f"TPSCheck.uk API v2 result sha256:{result.response_sha256}"
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            updated = await conn.fetchval(
                """
                UPDATE crm_tps_screening_jobs SET
                  screening_status = $3, screened_at = $4, provider_reference = $5,
                  result_sha256 = $6, result_payload = $7::jsonb,
                  last_http_status = $8, updated_at = NOW()
                WHERE id = $1 AND lease_token = $2 AND status = 'processing'
                RETURNING id
                """,
                job["id"],
                job["lease_token"],
                result.status,
                result.screened_at,
                reference,
                result.response_sha256,
                json.dumps(result.response),
                http_status,
            )
            if not updated:
                raise TpsCheckError("TPS job lease expired before its result was saved.", retryable=False)
            if usage_attempt_id is None:
                await conn.execute(
                    """
                    INSERT INTO crm_tps_usage_attempts (
                      organization_id, job_id, request_started_at, response_received_at,
                      outcome, screening_status, result_sha256, http_status
                    ) VALUES ($1, $2, $3, $3, 'result', $4, $5, $6)
                    """,
                    job["organization_id"],
                    job["id"],
                    result.screened_at,
                    result.status,
                    result.response_sha256,
                    http_status,
                )
            else:
                usage_updated = await conn.fetchval(
                    """
                    UPDATE crm_tps_usage_attempts SET
                      response_received_at = $3, outcome = 'result', screening_status = $4,
                      result_sha256 = $5, http_status = $6
                    WHERE id = $1 AND organization_id = $2 AND outcome = 'started'
                    RETURNING id
                    """,
                    usage_attempt_id,
                    job["organization_id"],
                    result.screened_at,
                    result.status,
                    result.response_sha256,
                    http_status,
                )
                if not usage_updated:
                    raise TpsCheckError(
                        "TPS usage reservation was not current when its result arrived.",
                        retryable=False,
                    )


def _saved_result(job: dict[str, Any]) -> TpsCheckResult | None:
    payload = coerce_json_object(job.get("result_payload"))
    if not payload:
        return None
    result = parse_tpscheck_result(payload, job["phone_e164"])
    saved_sha = job.get("result_sha256")
    if saved_sha != result.response_sha256:
        raise TpsCheckError("Saved TPSCheck result failed its integrity check.", retryable=False)
    screened_at = job.get("screened_at")
    if not isinstance(screened_at, datetime):
        raise TpsCheckError("Saved TPSCheck result has no screening timestamp.", retryable=False)
    return replace(result, screened_at=screened_at)


async def _persist_result(job: dict[str, Any], result: TpsCheckResult, http_status: int) -> None:
    reference = f"TPSCheck.uk API v2 result sha256:{result.response_sha256}"
    evidence = {
        "source": SOURCE,
        "reference": reference,
        "automatic": True,
        "result_sha256": result.response_sha256,
    }
    async with get_connection() as conn:
        async with conn.transaction():
            await _worker_context(conn)
            locked = await conn.fetchrow(
                """
                SELECT id FROM crm_tps_screening_jobs
                WHERE id = $1 AND lease_token = $2 AND status = 'processing'
                FOR UPDATE
                """,
                job["id"],
                job["lease_token"],
            )
            if not locked:
                raise TpsCheckError("TPS job lease is no longer current.", retryable=False)
            provider = await conn.fetchrow(
                """
                SELECT id, name, email, website, address_line1, address_line2,
                       town, county, postcode
                FROM care_providers WHERE id = $1
                """,
                job["provider_id"],
            )
            if not provider:
                raise TpsCheckError("The CQC provider record no longer exists.", retryable=False)
            address = ", ".join(
                str(provider[field]).strip()
                for field in ("address_line1", "address_line2", "town", "county", "postcode")
                if provider[field] and str(provider[field]).strip()
            )
            company_id = await conn.fetchval(
                """
                INSERT INTO crm_companies (
                  organization_id, name, website, phone_e164, address,
                  owner_user_id, created_by_user_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (organization_id, LOWER(name)) DO UPDATE SET
                  website = COALESCE(crm_companies.website, EXCLUDED.website),
                  phone_e164 = COALESCE(crm_companies.phone_e164, EXCLUDED.phone_e164),
                  address = COALESCE(crm_companies.address, EXCLUDED.address),
                  updated_at = NOW()
                RETURNING id
                """,
                job["organization_id"],
                provider["name"],
                provider["website"],
                result.phone_e164,
                address or None,
                job["assigned_user_id"],
                job["configured_by_user_id"],
            )
            contact = await conn.fetchrow(
                """
                SELECT id, provider_id, phone_e164, phone_screened_at
                FROM crm_contacts
                WHERE organization_id = $1
                  AND (provider_id = $2 OR phone_e164 = $3)
                ORDER BY (provider_id = $2) DESC, created_at
                LIMIT 1
                FOR UPDATE
                """,
                job["organization_id"],
                job["provider_id"],
                result.phone_e164,
            )
            if contact and contact["phone_e164"] not in (None, result.phone_e164):
                raise TpsCheckError(
                    "Existing CRM contact has a different phone number; manual review is required.",
                    retryable=False,
                )
            if contact:
                contact_id = contact["id"]
                await conn.execute(
                    """
                    UPDATE crm_contacts SET
                      company_id = COALESCE(company_id, $2),
                      company_name = COALESCE(company_name, $3),
                      email = COALESCE(email, $4), phone_e164 = COALESCE(phone_e164, $5),
                      owner_user_id = COALESCE(owner_user_id, $6), updated_at = NOW()
                    WHERE id = $1
                    """,
                    contact_id,
                    company_id,
                    provider["name"],
                    _safe_email(provider["email"]),
                    result.phone_e164,
                    job["assigned_user_id"],
                )
            else:
                email = _safe_email(provider["email"])
                if email:
                    email_exists = await conn.fetchval(
                        """
                        SELECT 1 FROM crm_contacts
                        WHERE organization_id = $1 AND LOWER(email) = $2
                        """,
                        job["organization_id"],
                        email,
                    )
                    if email_exists:
                        email = None
                contact_id = await conn.fetchval(
                    """
                    INSERT INTO crm_contacts (
                      organization_id, provider_id, company_id, owner_user_id,
                      created_by_user_id, company_name, email, phone_e164, lifecycle_stage
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'assigned')
                    RETURNING id
                    """,
                    job["organization_id"],
                    job["provider_id"],
                    company_id,
                    job["assigned_user_id"],
                    job["configured_by_user_id"],
                    provider["name"],
                    email,
                    result.phone_e164,
                )
                await conn.execute(
                    """
                    INSERT INTO crm_activities (
                      organization_id, contact_id, actor_user_id, activity_type, metadata
                    ) VALUES ($1, $2, NULL, 'contact_created',
                      jsonb_build_object('provider_id', $3::text, 'automatic', true))
                    """,
                    job["organization_id"],
                    contact_id,
                    job["provider_id"],
                )
            import_id = await conn.fetchval(
                """
                INSERT INTO crm_phone_screening_imports (
                  organization_id, imported_by_user_id, source, source_reference,
                  file_name, file_sha256, row_count, matched_count, clear_count, suppressed_count
                ) VALUES ($1, $2, $3, $4, 'tpscheck-api-v2.json', $5, 1, 1, $6, $7)
                RETURNING id
                """,
                job["organization_id"],
                job["configured_by_user_id"],
                SOURCE,
                reference,
                result.response_sha256,
                1 if result.status == "clear" else 0,
                0 if result.status == "clear" else 1,
            )
            await conn.execute(
                """
                INSERT INTO crm_phone_screening_cache (
                  organization_id, import_id, phone_hmac, status, source,
                  source_reference, screened_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (organization_id, phone_hmac) DO UPDATE SET
                  import_id = EXCLUDED.import_id, status = EXCLUDED.status,
                  source = EXCLUDED.source, source_reference = EXCLUDED.source_reference,
                  screened_at = EXCLUDED.screened_at, updated_at = NOW()
                WHERE EXCLUDED.screened_at >= crm_phone_screening_cache.screened_at
                """,
                job["organization_id"],
                import_id,
                hash_screening_number(result.phone_e164, settings.crm_screening_hash_key),
                result.status,
                SOURCE,
                reference,
                result.screened_at,
            )
            event_id = await conn.fetchval(
                """
                INSERT INTO crm_phone_screening_events (
                  organization_id, contact_id, screened_by_user_id, import_id,
                  phone_e164, status, source, source_reference, screened_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                job["organization_id"],
                contact_id,
                job["configured_by_user_id"],
                import_id,
                result.phone_e164,
                result.status,
                SOURCE,
                reference,
                result.screened_at,
            )
            await conn.execute(
                """
                UPDATE crm_contacts SET phone_screening_status = $2,
                  phone_screening_evidence = $3::jsonb, phone_screened_at = $4,
                  updated_at = NOW()
                WHERE id = $1
                """,
                contact_id,
                result.status,
                json.dumps(evidence),
                result.screened_at,
            )
            if result.status == "clear":
                await conn.execute(
                    """
                    DELETE FROM crm_suppressions
                    WHERE organization_id = $1 AND phone_e164 = $2 AND channel = 'call'
                      AND reason IN ('tps', 'ctps', 'invalid')
                    """,
                    job["organization_id"],
                    result.phone_e164,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO crm_suppressions (
                      organization_id, phone_e164, channel, reason, evidence, created_by_user_id
                    ) VALUES ($1, $2, 'call', $3, $4::jsonb, $5)
                    ON CONFLICT (organization_id, phone_e164, channel)
                      WHERE phone_e164 IS NOT NULL
                    DO UPDATE SET reason = EXCLUDED.reason, evidence = EXCLUDED.evidence
                    """,
                    job["organization_id"],
                    result.phone_e164,
                    result.status,
                    json.dumps({**evidence, "screening_event_id": str(event_id)}),
                    job["configured_by_user_id"],
                )
            await conn.execute(
                """
                INSERT INTO crm_activities (
                  organization_id, contact_id, actor_user_id, activity_type, metadata
                ) VALUES ($1, $2, NULL, 'phone_screened',
                  jsonb_build_object('status', $3::text, 'source', $4::text,
                                     'screening_event_id', $5::uuid, 'automatic', true))
                """,
                job["organization_id"],
                contact_id,
                result.status,
                SOURCE,
                event_id,
            )
            await conn.execute(
                """
                INSERT INTO audit_log (
                  action, outcome, actor_type, target_type, target_id, metadata
                ) VALUES ('crm.tps_automation.screen', 'success', 'system',
                  'crm_contact', $1::uuid::text,
                  jsonb_build_object('organization_id', $2::uuid::text,
                                     'status', $3::text, 'result_sha256', $4::text))
                """,
                contact_id,
                job["organization_id"],
                result.status,
                result.response_sha256,
            )
            await conn.execute(
                """
                UPDATE crm_tps_screening_jobs SET
                  contact_id = $3, status = 'completed', screening_status = $4,
                  screened_at = $5, provider_reference = $6, result_sha256 = $7,
                  last_http_status = $8, last_error = NULL, lease_token = NULL,
                  lease_expires_at = NULL, updated_at = NOW()
                WHERE id = $1 AND lease_token = $2
                """,
                job["id"],
                job["lease_token"],
                contact_id,
                result.status,
                result.screened_at,
                reference,
                result.response_sha256,
                http_status,
            )


async def process_tps_automation(*, limit: int = MAX_RUN_LIMIT) -> dict[str, Any]:
    """Process a bounded run below the Starter plan's 60 requests/minute limit."""
    if not settings.crm_tps_automation_enabled:
        return {"skipped": True, "reason": "disabled", "seeded": 0, "processed": 0}
    bounded_limit = max(1, min(limit, MAX_RUN_LIMIT))
    timeout = httpx.Timeout(5.0, connect=3.0)
    async with get_connection() as lock_conn:
        locked = await lock_conn.fetchval("SELECT pg_try_advisory_lock($1)", GLOBAL_LOCK_KEY)
        if not locked:
            return {"skipped": True, "reason": "overlap", "seeded": 0, "processed": 0}
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                try:
                    credits = await _fetch_credits(client)
                except TpsCheckError as exc:
                    await _record_run_error(str(exc))
                    raise
                remaining = max(0, int(credits["requests_remaining"]))
                seeded = await seed_tps_jobs(per_organization_limit=max(250, bounded_limit * 5))
                run_limit = min(await _configured_run_limit(bounded_limit), remaining)
                counts = {
                    "checked": 0,
                    "processed": 0,
                    "clear": 0,
                    "suppressed": 0,
                    "failed": 0,
                }
                loop = asyncio.get_running_loop()
                run_started_at = loop.time()
                next_request_at = 0.0
                for _ in range(run_limit):
                    if loop.time() - run_started_at >= RUN_BUDGET_SECONDS:
                        break
                    job = await _claim_job()
                    if not job:
                        break
                    usage_attempt_id = None
                    provider_result_saved = False
                    try:
                        result = _saved_result(job)
                        provider_result_saved = result is not None
                        http_status = int(job.get("last_http_status") or 200)
                        if result is None:
                            delay = next_request_at - loop.time()
                            if delay > 0:
                                await asyncio.sleep(delay)
                            next_request_at = loop.time() + REQUEST_SPACING_SECONDS
                            usage_attempt_id = await _reserve_usage_attempt(job)
                            counts["checked"] += 1
                            result, http_status = await _screen_phone(client, job["phone_e164"])
                            try:
                                await _record_provider_result(
                                    job, result, http_status, usage_attempt_id
                                )
                                provider_result_saved = True
                            except TpsCheckError:
                                raise
                            except Exception as exc:
                                logger.exception("TPS result could not be durably recorded for job %s", job["id"])
                                raise TpsCheckError(
                                    "TPSCheck result could not be durably recorded; reconciliation is required.",
                                    retryable=False,
                                ) from exc
                        await _persist_result(job, result, http_status)
                        counts["processed"] += 1
                        if result.status == "clear":
                            counts["clear"] += 1
                        else:
                            counts["suppressed"] += 1
                    except TpsCheckError as exc:
                        if usage_attempt_id is not None and not provider_result_saved:
                            try:
                                await _record_usage_ambiguous(job, usage_attempt_id, exc.http_status)
                            except Exception:
                                logger.exception(
                                    "TPS ambiguous usage could not be updated for job %s", job["id"]
                                )
                        await _mark_failure(job, exc)
                        counts["failed"] += 1
                        if exc.http_status in {401, 403, 429}:
                            logger.error("TPS automation stopped after provider response: %s", exc)
                            break
                    except Exception:
                        logger.exception("TPS CRM materialisation failed for job %s", job["id"])
                        if usage_attempt_id is not None and not provider_result_saved:
                            try:
                                await _record_usage_ambiguous(job, usage_attempt_id, None)
                            except Exception:
                                logger.exception(
                                    "TPS ambiguous usage could not be updated for job %s", job["id"]
                                )
                        await _mark_failure(
                            job,
                            TpsCheckError("CRM materialisation failed; the saved result will be retried."),
                        )
                        counts["failed"] += 1
                async with get_connection() as conn:
                    async with conn.transaction():
                        await _worker_context(conn)
                        await conn.execute(
                            """
                            UPDATE crm_tps_automation_settings SET
                              last_run_at = NOW(),
                              last_success_at = CASE WHEN $1::int = 0 THEN last_success_at ELSE NOW() END,
                              last_error = CASE WHEN $2::int = 0 THEN NULL ELSE $3 END,
                              updated_at = NOW()
                            WHERE enabled = TRUE
                            """,
                            counts["processed"],
                            counts["failed"],
                            "One or more TPSCheck jobs failed; see the durable job queue.",
                        )
                return {
                    "skipped": False,
                    "seeded": seeded,
                    "provider_plan": credits["plan"],
                    "credits_remaining_before_run": remaining,
                    **counts,
                }
        finally:
            await lock_conn.execute("SELECT pg_advisory_unlock($1)", GLOBAL_LOCK_KEY)
