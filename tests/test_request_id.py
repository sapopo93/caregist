"""Tests for request-id propagation and log correlation (F-39)."""

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.logging_config import JSONFormatter, RequestIdFilter, request_id_var
from api.middleware.request_id import RequestIdMiddleware, _normalize


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/probe")
    def probe():
        # The ContextVar set by the middleware must be visible in the handler.
        return {"request_id": request_id_var.get()}

    return app


def test_response_has_generated_request_id():
    client = TestClient(_make_app())
    resp = client.get("/probe")
    header_id = resp.headers["X-Request-ID"]
    assert header_id
    # The handler saw the same id the response advertises (ContextVar propagated).
    assert resp.json()["request_id"] == header_id


def test_valid_client_request_id_is_echoed():
    client = TestClient(_make_app())
    resp = client.get("/probe", headers={"X-Request-ID": "abc-123-def"})
    assert resp.headers["X-Request-ID"] == "abc-123-def"
    assert resp.json()["request_id"] == "abc-123-def"


def test_malicious_request_id_is_replaced():
    client = TestClient(_make_app())
    bad = "x" * 200 + " evil\r\nInjected: 1"
    resp = client.get("/probe", headers={"X-Request-ID": bad})
    assert resp.headers["X-Request-ID"] != bad
    assert len(resp.headers["X-Request-ID"]) == 32  # minted uuid4 hex


def test_request_id_context_var_resets_after_request():
    client = TestClient(_make_app())
    client.get("/probe")
    # Outside any request the var is back to its default.
    assert request_id_var.get() is None


def test_normalize_rules():
    assert _normalize("simple-id-123") == "simple-id-123"
    assert _normalize(None) is not None and len(_normalize(None)) == 32
    assert _normalize("has space") != "has space"


def test_json_formatter_includes_request_id():
    token = request_id_var.set("rid-xyz")
    try:
        record = logging.LogRecord("n", logging.INFO, __file__, 1, "hello", None, None)
        RequestIdFilter().filter(record)
        payload = json.loads(JSONFormatter().format(record))
        assert payload["request_id"] == "rid-xyz"
    finally:
        request_id_var.reset(token)
