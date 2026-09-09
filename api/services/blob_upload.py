"""Minimal Vercel Blob upload client for server-side fulfilment.

The existing paid-download route (``frontend/app/api/export/route.ts``) already
reads artefacts back from Vercel Blob with a short-lived presigned private URL.
Nothing in the Python codebase *writes* to Blob yet - the retired full-dataset
artefact was provisioned out of band. The Territory Opportunity Brief is
generated per order inside the Stripe webhook, so the fulfilment path needs to
upload the generated PDF and CSV itself.

This uploads with a caller-chosen, unguessable pathname and no random suffix, so
the returned pathname is deterministic for the caller and the object is only
reachable through the entitlement + presign flow, never a guessable public URL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

_BLOB_API = "https://blob.vercel-storage.com"
_API_VERSION = "7"


class BlobUploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlobObject:
    pathname: str
    url: str
    download_url: str
    content_type: str
    size: int


def put_blob(
    pathname: str,
    data: bytes,
    *,
    content_type: str,
    token: str,
    timeout: float = 30.0,
) -> BlobObject:
    """Upload ``data`` to Vercel Blob at ``pathname``. Private store assumed.

    Raises :class:`BlobUploadError` on any non-2xx response or malformed body.
    """
    if not token:
        raise BlobUploadError("BLOB_READ_WRITE_TOKEN is not configured")
    if not pathname or pathname.startswith("/") or ".." in pathname:
        raise BlobUploadError(f"unsafe blob pathname: {pathname!r}")

    headers = {
        "authorization": f"Bearer {token}",
        "x-api-version": _API_VERSION,
        "x-content-type": content_type,
        # Deterministic pathname: the caller supplies the unguessable segment.
        "x-add-random-suffix": "0",
        # Long cache once delivered; the entitlement layer controls access.
        "x-cache-control-max-age": "31536000",
    }
    try:
        response = httpx.put(
            f"{_BLOB_API}/{pathname}",
            content=data,
            headers=headers,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - network failure path
        raise BlobUploadError(f"blob upload transport error: {exc}") from exc

    if response.status_code // 100 != 2:
        raise BlobUploadError(
            f"blob upload failed: HTTP {response.status_code} {response.text[:300]}"
        )
    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise BlobUploadError("blob upload returned a non-JSON body") from exc

    returned_pathname = body.get("pathname") or pathname
    url = body.get("url")
    if not url:
        raise BlobUploadError(f"blob upload response missing url: {body!r}")
    return BlobObject(
        pathname=returned_pathname,
        url=url,
        download_url=body.get("downloadUrl") or url,
        content_type=content_type,
        size=len(data),
    )
