"""Bounded, retry-safe ingestion of Twilio recordings into private storage."""

from __future__ import annotations

from typing import Any

from api.config import settings
from api.database import get_connection
from api.services.crm_recordings import (
    download_twilio_recording,
    twilio_recording_url,
    upload_recording,
)


async def _claim_recording_job() -> dict[str, Any] | None:
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_recording_ingest', true)")
            row = await conn.fetchrow(
                """
                WITH candidate AS (
                  SELECT recording.id
                  FROM crm_recordings recording
                  WHERE (
                      recording.status IN ('queued', 'error')
                      OR (
                        recording.status = 'uploading'
                        AND recording.processing_started_at < NOW() - INTERVAL '15 minutes'
                      )
                    )
                    AND recording.attempts < 5
                    AND recording.expires_at > NOW()
                  ORDER BY recording.created_at
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE crm_recordings recording
                SET status = 'uploading', attempts = attempts + 1,
                    processing_started_at = NOW(), error_code = NULL, updated_at = NOW()
                FROM candidate, crm_call_sessions call
                WHERE recording.id = candidate.id
                  AND call.id = recording.call_session_id
                RETURNING recording.id, recording.organization_id,
                          recording.call_session_id, recording.twilio_recording_sid,
                          recording.object_key, call.contact_id
                """
            )
    return dict(row) if row else None


async def process_recording_jobs(*, limit: int = 1) -> dict[str, int]:
    """Secure a small number of recordings; safe for a bounded cron invocation."""
    if not settings.crm_recording_enabled:
        return {"processed": 0, "failed": 0}
    processed = failed = 0
    for _ in range(max(0, min(limit, 5))):
        job = await _claim_recording_job()
        if not job:
            break
        try:
            content = await download_twilio_recording(
                twilio_recording_url(job["twilio_recording_sid"])
            )
            digest = await upload_recording(job["object_key"], content)
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "SELECT set_config('caregist.worker', 'crm_recording_ingest', true)"
                    )
                    updated = await conn.fetchval(
                        """
                        UPDATE crm_recordings SET
                          status = 'ready', content_type = 'audio/mpeg',
                          byte_size = $2, sha256 = $3, processing_started_at = NULL,
                          error_code = NULL, updated_at = NOW()
                        WHERE id = $1 AND status = 'uploading'
                        RETURNING id
                        """,
                        job["id"], len(content), digest,
                    )
                    if not updated:
                        raise RuntimeError("Recording job no longer owns the upload claim.")
                    await conn.execute(
                        """
                        INSERT INTO crm_activities (
                          organization_id, contact_id, activity_type, metadata
                        ) VALUES (
                          $1, $2, 'recording_available',
                          jsonb_build_object('recording_id', $3::uuid)
                        )
                        """,
                        job["organization_id"], job["contact_id"], job["id"],
                    )
                    if settings.crm_ai_enabled:
                        await conn.execute(
                            """
                            INSERT INTO crm_call_intelligence (
                              organization_id, call_session_id, recording_id
                            ) VALUES ($1, $2, $3)
                            ON CONFLICT (call_session_id) DO NOTHING
                            """,
                            job["organization_id"], job["call_session_id"], job["id"],
                        )
            processed += 1
        except Exception as exc:
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "SELECT set_config('caregist.worker', 'crm_recording_ingest', true)"
                    )
                    await conn.execute(
                        """
                        UPDATE crm_recordings
                        SET status = 'error', error_code = $2,
                            processing_started_at = NULL, updated_at = NOW()
                        WHERE id = $1 AND status = 'uploading'
                        """,
                        job["id"], type(exc).__name__[:80],
                    )
            failed += 1
    return {"processed": processed, "failed": failed}
