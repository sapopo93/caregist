from __future__ import annotations

import json
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import uuid4

import pytest
import httpx

from api.services import crm_ai
from api.services.crm_ai import RedactedTranscript, evaluate_transcript, redact_transcript


def _valid_evaluation() -> dict:
    return {
        "summary": "The contact requested a later conversation.",
        "suggested_disposition": "callback_requested",
        "overall_qa_score": 84,
        "customer_sentiment": "neutral",
        "outcome": "Follow-up requested",
        "strengths": ["Clear opening"],
        "coaching_actions": ["Confirm the next step"],
        "compliance_flags": [],
    }


def test_redaction_removes_names_contact_details_identifiers_and_sensitive_lines():
    source = (
        "[0000.00] Agent: Hello, this is Alice Jones from CareGist.\n"
        "[0001.20] Contact: My name is Bob Smith. Call +44 7700 900123 or email "
        "bob.smith@example.com.\n"
        "[0003.10] Contact: My National Insurance number is QQ 12 34 56 C.\n"
        "[0004.00] Contact: I have a medical diagnosis and my postcode is SW1A 1AA."
    )

    result = redact_transcript(
        source,
        known_entities=("Alice Jones", "Bob Smith", "CareGist"),
    )

    for private_value in (
        "Alice", "Jones", "Bob", "Smith", "CareGist", "+44 7700 900123",
        "bob.smith@example.com", "QQ 12 34 56 C", "medical diagnosis", "SW1A 1AA",
    ):
        assert private_value.lower() not in result.text.lower()
    assert "[REDACTED NAME]" in result.text
    assert "[REDACTED EMAIL]" in result.text
    assert "[REDACTED PHONE]" in result.text
    assert "[REDACTED SENSITIVE INFORMATION]" in result.text
    assert result.source_sha256 != result.redacted_sha256
    assert result.evidence()["policy_version"] == "caregist-crm-redaction-v1"


def test_redaction_rejects_empty_and_oversized_transcripts():
    with pytest.raises(crm_ai.RedactionError):
        redact_transcript("   ")
    with pytest.raises(crm_ai.RedactionError):
        redact_transcript("x" * 120_001)


@pytest.mark.parametrize(
    "source,private_value",
    [
        ("Contact: please ask sarah williams about that.", "sarah williams"),
        ("Contact: please ask MCDONALD about that.", "MCDONALD"),
        ("Contact: my cancer treatment starts tomorrow.", "cancer treatment"),
        ("Contact: my chemotherapy appointment is private.", "chemotherapy"),
    ],
)
def test_redaction_blocks_adversarial_name_casing_and_special_category_data(
    source: str, private_value: str
):
    result = redact_transcript(source)
    assert private_value.lower() not in result.text.lower()
    assert "[REDACTED" in result.text


def test_local_ner_redacts_uncued_lowercase_third_party_names():
    for name in ("sarah williams", "xavier quinn", "siobhan oconnor"):
        result = redact_transcript(
            f"Contact: I met {name} yesterday.",
            require_local_ner=True,
        )
        assert name not in result.text.lower()
        assert result.counts["local_ner_entity"] >= 1


@pytest.mark.asyncio
async def test_deepseek_receives_only_redacted_text_and_retries_invalid_json(monkeypatch):
    redacted = RedactedTranscript(
        text="[0000.00] Agent: Hello [REDACTED NAME].",
        counts={"known_name": 1},
        source_sha256="a" * 64,
        redacted_sha256="b" * 64,
    )
    responses = [
        {"id": "bad-empty", "choices": [{"finish_reason": "stop", "message": {"content": ""}}]},
        {"id": "bad-json", "choices": [{"finish_reason": "stop", "message": {"content": "{"}}]},
        {
            "id": "request-3",
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(_valid_evaluation())}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "prompt_tokens_details": {"cached_tokens": 20},
            },
        },
    ]
    requests: list[dict] = []

    class Response:
        def __init__(self, payload: dict):
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, *, headers, json):
            requests.append({"headers": headers, "json": json})
            return Response(responses.pop(0))

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr(crm_ai.httpx, "AsyncClient", Client)
    monkeypatch.setattr(crm_ai.asyncio, "sleep", no_wait)
    monkeypatch.setattr(crm_ai.settings, "crm_ai_api_key", "memory-only-test-key")
    monkeypatch.setattr(crm_ai.settings, "crm_ai_model", "deepseek-v4-flash")
    monkeypatch.setattr(crm_ai.settings, "crm_ai_input_price_usd_per_million", Decimal("0.14"))
    monkeypatch.setattr(crm_ai.settings, "crm_ai_cache_hit_price_usd_per_million", Decimal("0.0028"))
    monkeypatch.setattr(crm_ai.settings, "crm_ai_output_price_usd_per_million", Decimal("0.28"))

    evaluation, usage = await evaluate_transcript(redacted, user_id="c" * 64)

    assert evaluation.overall_qa_score == 84
    assert usage.request_id == "request-3"
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cost_usd > 0
    assert len(requests) == 3
    for request in requests:
        serialized = json.dumps(request["json"])
        assert "Alice" not in serialized
        assert "memory-only-test-key" not in serialized
        assert request["json"]["thinking"] == {"type": "disabled"}
        assert request["json"]["model"] == "deepseek-v4-flash"
        assert request["json"]["user_id"] == "c" * 64


@pytest.mark.asyncio
async def test_ambiguous_provider_attempts_use_auditable_maximum_tokens(monkeypatch):
    redacted = RedactedTranscript(
        text="Contact: [REDACTED NAME] requested a callback.",
        counts={"local_ner_entity": 1},
        source_sha256="a" * 64,
        redacted_sha256="b" * 64,
    )
    recorded: list[dict] = []

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("ambiguous provider outcome")

    async def record(**kwargs):
        recorded.append(kwargs)

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr(crm_ai.httpx, "AsyncClient", Client)
    monkeypatch.setattr(crm_ai, "_record_usage_attempt", record)
    monkeypatch.setattr(crm_ai.asyncio, "sleep", no_wait)

    with pytest.raises(RuntimeError, match="no valid schema-bound evaluation"):
        await evaluate_transcript(
            redacted,
            user_id="c" * 64,
            intelligence_id=uuid4(),
        )

    assert len(recorded) == crm_ai.MAX_EVALUATION_ATTEMPTS
    assert all(item["input_tokens"] == 500_000 for item in recorded)
    assert all(item["output_tokens"] == 1_200 for item in recorded)
    assert all(item["cost_usd"] == crm_ai.maximum_request_cost_usd() for item in recorded)


def test_cost_calculation_uses_provider_reported_tokens(monkeypatch):
    monkeypatch.setattr(crm_ai.settings, "crm_ai_input_price_usd_per_million", Decimal("0.14"))
    monkeypatch.setattr(crm_ai.settings, "crm_ai_cache_hit_price_usd_per_million", Decimal("0.0028"))
    monkeypatch.setattr(crm_ai.settings, "crm_ai_output_price_usd_per_million", Decimal("0.28"))
    assert crm_ai.calculate_cost_usd(
        input_tokens=1_000_000,
        cache_hit_input_tokens=250_000,
        output_tokens=100_000,
    ) == Decimal("0.13370000")


def test_maximum_request_cost_reserves_utf8_byte_ceiling(monkeypatch):
    monkeypatch.setattr(crm_ai.settings, "crm_ai_input_price_usd_per_million", Decimal("0.14"))
    monkeypatch.setattr(crm_ai.settings, "crm_ai_cache_hit_price_usd_per_million", Decimal("0.0028"))
    monkeypatch.setattr(crm_ai.settings, "crm_ai_output_price_usd_per_million", Decimal("0.28"))

    assert crm_ai.maximum_request_cost_usd() == crm_ai.calculate_cost_usd(
        input_tokens=500_000,
        output_tokens=1_200,
    )


@pytest.mark.asyncio
async def test_usage_ledger_releases_exactly_one_attempt_reservation(monkeypatch):
    statements: list[tuple[str, tuple]] = []

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    class Connection:
        def transaction(self):
            return Transaction()

        async def execute(self, statement, *args):
            statements.append((statement, args))

    @asynccontextmanager
    async def connection():
        yield Connection()

    monkeypatch.setattr(crm_ai, "get_connection", connection)
    intelligence_id = uuid4()
    await crm_ai._record_usage_attempt(
        intelligence_id=intelligence_id,
        request_id="provider-request",
        input_tokens=50,
        output_tokens=10,
        cached_tokens=0,
        cost_usd=Decimal("0.00000980"),
        schema_valid=True,
    )

    reservation_updates = [item for item in statements if "GREATEST(reserved_cost_usd" in item[0]]
    assert len(reservation_updates) == 1
    assert reservation_updates[0][1] == (intelligence_id, crm_ai.maximum_request_cost_usd())


@pytest.mark.asyncio
async def test_claim_budget_preserves_selected_hold_and_counts_cross_month_processing(monkeypatch):
    job_id = uuid4()
    queries: list[tuple[str, tuple]] = []

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    class Connection:
        def __init__(self):
            self.fetchrow_calls = 0

        def transaction(self):
            return Transaction()

        async def execute(self, statement, *args):
            queries.append((statement, args))

        async def fetchrow(self, statement, *args):
            queries.append((statement, args))
            self.fetchrow_calls += 1
            if self.fetchrow_calls == 1:
                return {
                    "id": job_id,
                    "organization_id": uuid4(),
                    "call_session_id": uuid4(),
                    "attempts": 1,
                    "existing_reservation": Decimal("0.25"),
                    "object_key": "recording.wav",
                    "first_name": "Test",
                    "last_name": "Contact",
                    "company_name": "Example",
                    "agent_name": "Agent",
                }
            return {"attempts": 2}

        async def fetchval(self, statement, *args):
            queries.append((statement, args))
            return Decimal("0")

    @asynccontextmanager
    async def connection():
        yield Connection()

    monkeypatch.setattr(crm_ai, "get_connection", connection)
    monkeypatch.setattr(crm_ai.settings, "crm_ai_monthly_cap_usd", Decimal("100"))

    claimed = await crm_ai._claim_job()

    assert claimed is not None
    budget_query, budget_args = next(
        item for item in queries if "SUM(reserved_cost_usd)" in item[0]
    )
    assert "status = 'processing'" in budget_query
    assert "status = 'failed'" in budget_query
    assert "status IN ('completed', 'purged')" in budget_query
    assert "updated_at >= date_trunc('month', NOW())" in budget_query
    assert "processed_at >= date_trunc('month', NOW())" in budget_query
    assert "id <>" not in budget_query
    assert budget_args == ()
    claim_update, claim_args = next(
        item for item in queries if "reserved_cost_usd = $2 + $3" in item[0]
    )
    assert claim_update
    assert claim_args == (
        job_id,
        crm_ai.maximum_request_cost_usd() * crm_ai.MAX_EVALUATION_ATTEMPTS,
        Decimal("0.25"),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("usage_persistence_failed", [False, True])
async def test_job_failure_releases_unused_holds_but_keeps_ambiguous_charge(
    monkeypatch, usage_persistence_failed: bool
):
    job = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "call_session_id": uuid4(),
        "attempts": 2,
        "existing_reservation": Decimal("0.25"),
        "object_key": "synthetic.wav",
        "first_name": "Synthetic",
        "last_name": "Contact",
        "company_name": "Example",
        "agent_name": "Agent",
    }
    failure_updates: list[tuple] = []

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    class Connection:
        def transaction(self):
            return Transaction()

        async def execute(self, statement, *args):
            if "reserved_cost_usd = $4" in statement:
                failure_updates.append(args)

    @asynccontextmanager
    async def connection():
        yield Connection()

    async def claim():
        return job

    async def local_failure(_key):
        raise RuntimeError("local transcription input unavailable")

    async def load(_key):
        return b"synthetic"

    async def transcribe(_audio):
        return "Contact: synthetic callback requested."

    async def current(_job):
        return True

    async def persistence_failure(*_args, **_kwargs):
        raise crm_ai.ProviderUsagePersistenceError("usage ledger unavailable")

    monkeypatch.setattr(crm_ai.settings, "crm_ai_enabled", True)
    monkeypatch.setattr(crm_ai, "get_connection", connection)
    monkeypatch.setattr(crm_ai, "_claim_job", claim)
    if usage_persistence_failed:
        monkeypatch.setattr(crm_ai, "load_recording_object", load)
        monkeypatch.setattr(crm_ai, "transcribe_dual_channel", transcribe)
        monkeypatch.setattr(crm_ai, "redact_transcript", lambda *_args, **_kwargs: RedactedTranscript(
            text="Contact: callback requested.", counts={},
            source_sha256="a" * 64, redacted_sha256="b" * 64,
        ))
        monkeypatch.setattr(crm_ai, "pseudonymous_user_id", lambda _id: "c" * 64)
        monkeypatch.setattr(crm_ai, "_job_is_current", current)
        monkeypatch.setattr(crm_ai, "evaluate_transcript", persistence_failure)
    else:
        monkeypatch.setattr(crm_ai, "load_recording_object", local_failure)

    result = await crm_ai.process_ai_jobs(limit=1)

    assert result == {"processed": 0, "failed": 1}
    expected = Decimal("0.25")
    if usage_persistence_failed:
        expected += crm_ai.maximum_request_cost_usd()
    assert failure_updates == [
        (job["id"], (
            "ProviderUsagePersistenceError" if usage_persistence_failed else "RuntimeError"
        ), job["attempts"], expected)
    ]
