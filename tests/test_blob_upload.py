"""Unit tests for the Vercel Blob upload helper (no network)."""

from __future__ import annotations

import httpx
import pytest

from api.services import blob_upload
from api.services.blob_upload import BlobObject, BlobUploadError, put_blob


class _Resp:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = body if isinstance(body, str) else ""

    def json(self):
        import json

        if isinstance(self._body, dict):
            return self._body
        return json.loads(self._body)


def test_put_blob_success(monkeypatch):
    captured = {}

    def fake_put(url, content, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["content"] = content
        return _Resp(200, {"url": "https://blob.example/abc", "pathname": "p/brief.pdf",
                            "downloadUrl": "https://blob.example/abc?download=1"})

    monkeypatch.setattr(blob_upload.httpx, "put", fake_put)
    obj = put_blob("p/brief.pdf", b"data", content_type="application/pdf", token="vercel_blob_rw_xxx")
    assert isinstance(obj, BlobObject)
    assert obj.pathname == "p/brief.pdf"
    assert obj.url == "https://blob.example/abc"
    assert obj.size == 4
    assert captured["headers"]["authorization"] == "Bearer vercel_blob_rw_xxx"
    assert captured["headers"]["x-add-random-suffix"] == "0"
    assert captured["url"].endswith("/p/brief.pdf")


def test_put_blob_rejects_missing_token():
    with pytest.raises(BlobUploadError, match="not configured"):
        put_blob("p/x.pdf", b"d", content_type="application/pdf", token="")


@pytest.mark.parametrize("bad", ["/leading", "a/../b", "../escape"])
def test_put_blob_rejects_unsafe_pathname(bad):
    with pytest.raises(BlobUploadError, match="unsafe"):
        put_blob(bad, b"d", content_type="application/pdf", token="t")


def test_put_blob_raises_on_non_2xx(monkeypatch):
    monkeypatch.setattr(blob_upload.httpx, "put", lambda *a, **k: _Resp(403, "Forbidden"))
    with pytest.raises(BlobUploadError, match="HTTP 403"):
        put_blob("p/x.pdf", b"d", content_type="application/pdf", token="t")


def test_put_blob_raises_on_missing_url(monkeypatch):
    monkeypatch.setattr(blob_upload.httpx, "put", lambda *a, **k: _Resp(200, {"pathname": "p"}))
    with pytest.raises(BlobUploadError, match="missing url"):
        put_blob("p/x.pdf", b"d", content_type="application/pdf", token="t")


def test_put_blob_wraps_transport_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(blob_upload.httpx, "put", boom)
    with pytest.raises(BlobUploadError, match="transport error"):
        put_blob("p/x.pdf", b"d", content_type="application/pdf", token="t")
