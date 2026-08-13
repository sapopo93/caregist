"""Private call-recording storage and deterministic 30-day retention."""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import UTC, datetime
from functools import partial
from urllib.parse import urlparse
from uuid import UUID

import httpx

from api.config import settings


MAX_RECORDING_BYTES = 100 * 1024 * 1024
TWILIO_RECORDING_SID = re.compile(r"^RE[0-9a-fA-F]{32}$")


def validate_twilio_recording_url(value: str) -> str:
    """Reject non-Twilio and non-HTTPS recording URLs to prevent SSRF."""
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not hostname.endswith(".twilio.com"):
        raise ValueError("Twilio recording URL is not an approved HTTPS host.")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Twilio recording URL is malformed.")
    path = parsed.path.rstrip("/")
    if not path.lower().endswith(".mp3"):
        path += ".mp3"
    return parsed._replace(path=path).geturl()


def validate_twilio_recording_sid(recording_sid: str) -> str:
    if not TWILIO_RECORDING_SID.fullmatch(recording_sid):
        raise ValueError("Twilio recording SID is invalid.")
    return recording_sid


def twilio_recording_url(recording_sid: str) -> str:
    """Build the account-bound dual-channel media URL without persisting callback URLs."""
    validate_twilio_recording_sid(recording_sid)
    if not settings.twilio_account_sid.startswith("AC"):
        raise RuntimeError("Twilio account SID is not configured.")
    return validate_twilio_recording_url(
        "https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Recordings/{recording_sid}.mp3?RequestedChannels=2"
    )


def validate_mp3_payload(content: bytes) -> None:
    """Reject empty or obviously non-MP3 provider bodies before private storage."""
    if len(content) < 4:
        raise ValueError("Twilio returned an empty or malformed recording.")
    if content[:3] == b"ID3":
        return
    if content[0] == 0xFF and content[1] & 0xE0 == 0xE0:
        return
    raise ValueError("Twilio returned a non-MP3 recording payload.")


def recording_object_key(organization_id: UUID, call_session_id: UUID, recorded_at: datetime) -> str:
    instant = recorded_at.astimezone(UTC)
    return (
        f"crm-recordings/{organization_id}/{instant:%Y/%m/%d}/"
        f"{call_session_id}.mp3"
    )


def _storage_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.crm_recording_s3_endpoint_url,
        region_name=settings.crm_recording_s3_region,
        aws_access_key_id=settings.crm_recording_s3_access_key_id,
        aws_secret_access_key=settings.crm_recording_s3_secret_access_key,
    )


async def download_twilio_recording(recording_url: str) -> bytes:
    url = validate_twilio_recording_url(recording_url)
    async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
        async with client.stream(
            "GET",
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        ) as response:
            response.raise_for_status()
            advertised_size = int(response.headers.get("content-length", "0") or 0)
            if advertised_size > MAX_RECORDING_BYTES:
                raise ValueError("Recording exceeds the approved size limit.")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_RECORDING_BYTES:
                    raise ValueError("Recording exceeds the approved size limit.")
    if not content:
        raise ValueError("Twilio returned an empty recording.")
    result = bytes(content)
    validate_mp3_payload(result)
    return result


async def upload_recording(object_key: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    client = _storage_client()
    upload = partial(
        client.put_object,
        Bucket=settings.crm_recording_s3_bucket,
        Key=object_key,
        Body=content,
        ContentType="audio/mpeg",
        ServerSideEncryption="AES256",
        Metadata={"sha256": digest, "retention-days": "30"},
    )
    await asyncio.to_thread(upload)
    return digest


async def delete_recording_object(object_key: str) -> None:
    client = _storage_client()
    await asyncio.to_thread(
        partial(client.delete_object, Bucket=settings.crm_recording_s3_bucket, Key=object_key)
    )


async def load_recording_object(object_key: str) -> bytes:
    client = _storage_client()
    response = await asyncio.to_thread(
        partial(client.get_object, Bucket=settings.crm_recording_s3_bucket, Key=object_key)
    )
    body = response["Body"]
    content = await asyncio.to_thread(body.read)
    if len(content) > MAX_RECORDING_BYTES:
        raise ValueError("Stored recording exceeds the approved size limit.")
    return content


async def presign_recording(object_key: str, *, expires_seconds: int = 60) -> str:
    client = _storage_client()
    return await asyncio.to_thread(
        partial(
            client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": settings.crm_recording_s3_bucket,
                "Key": object_key,
                "ResponseContentType": "audio/mpeg",
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=expires_seconds,
        )
    )


async def delete_twilio_source(recording_sid: str) -> bool:
    """Remove Twilio's copy once the encrypted object has been verified uploaded."""
    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        await asyncio.to_thread(client.recordings(recording_sid).delete)
        return True
    except Exception as exc:
        # Twilio returns 404 when an earlier retry already removed the source.
        # Absence is the required post-condition, so treat it as success.
        if getattr(exc, "status", None) == 404:
            return True
        return False
