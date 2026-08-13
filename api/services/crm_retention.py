"""Recording-retention worker; object deletion is authoritative and audited."""

from __future__ import annotations

from api.database import get_connection
from api.services.crm_recordings import delete_recording_object, delete_twilio_source


async def cleanup_twilio_sources(*, limit: int = 50) -> dict[str, int]:
    """Retry deletion of secured Twilio source copies until confirmed removed."""
    deleted = failed = 0
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
            rows = await conn.fetch(
                """
                WITH candidates AS (
                  SELECT id
                  FROM crm_recordings
                  WHERE status IN ('ready', 'deleted')
                    AND source_deleted_at IS NULL
                    AND (
                      error_code IS DISTINCT FROM 'twilio_source_delete_processing'
                      OR updated_at < NOW() - INTERVAL '15 minutes'
                    )
                  ORDER BY created_at
                  FOR UPDATE SKIP LOCKED
                  LIMIT $1
                )
                UPDATE crm_recordings recording
                SET error_code = 'twilio_source_delete_processing', updated_at = NOW()
                FROM candidates
                WHERE recording.id = candidates.id
                RETURNING recording.id, recording.twilio_recording_sid
                """,
                max(1, min(limit, 200)),
            )
    for row in rows:
        if await delete_twilio_source(row["twilio_recording_sid"]):
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
                    await conn.execute(
                        """
                        UPDATE crm_recordings
                        SET source_deleted_at = NOW(), error_code = NULL, updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                    )
            deleted += 1
        else:
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
                    await conn.execute(
                        """
                        UPDATE crm_recordings
                        SET error_code = 'twilio_source_delete_failed', updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                    )
            failed += 1
    return {"deleted": deleted, "failed": failed}


async def purge_expired_recordings(*, limit: int = 50) -> dict[str, int]:
    deleted = failed = sources_deleted = 0
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
            rows = await conn.fetch(
                """
                WITH candidates AS (
                  SELECT id
                  FROM crm_recordings
                  WHERE expires_at <= NOW()
                    AND (
                      status IN ('queued', 'ready', 'error')
                      OR (
                        status = 'uploading'
                        AND processing_started_at < NOW() - INTERVAL '15 minutes'
                      )
                      OR (
                        status = 'deleting'
                        AND updated_at < NOW() - INTERVAL '15 minutes'
                      )
                    )
                  ORDER BY expires_at
                  FOR UPDATE SKIP LOCKED
                  LIMIT $1
                )
                UPDATE crm_recordings recording
                SET status = 'deleting', error_code = NULL, updated_at = NOW()
                FROM candidates
                WHERE recording.id = candidates.id
                RETURNING recording.id, recording.object_key, recording.twilio_recording_sid
                """,
                max(1, min(limit, 200)),
            )
            if rows:
                await conn.execute(
                    """
                    UPDATE crm_call_intelligence
                    SET status = 'purged', transcript = NULL, summary = NULL,
                        evaluation = NULL, redaction_summary = NULL,
                        external_user_id = NULL, external_request_id = NULL,
                        error_code = NULL,
                        processed_at = CASE
                          WHEN reserved_cost_usd > 0
                            THEN COALESCE(processed_at, updated_at)
                          ELSE processed_at
                        END,
                        updated_at = NOW()
                    WHERE recording_id = ANY($1::uuid[])
                    """,
                    [row["id"] for row in rows],
                )
    for row in rows:
        object_error: str | None = None
        try:
            await delete_recording_object(row["object_key"])
        except Exception as exc:
            object_error = type(exc).__name__[:80]
        source_deleted = await delete_twilio_source(row["twilio_recording_sid"])
        if source_deleted:
            sources_deleted += 1
        if object_error is None:
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
                    await conn.execute(
                        """
                        UPDATE crm_recordings
                        SET status = 'deleted', deleted_at = NOW(),
                            source_deleted_at = CASE
                              WHEN $2 THEN COALESCE(source_deleted_at, NOW())
                              ELSE source_deleted_at
                            END,
                            error_code = CASE
                              WHEN $2 THEN NULL ELSE 'twilio_source_delete_failed'
                            END,
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"], source_deleted,
                    )
                    await conn.execute(
                        """
                        INSERT INTO audit_log (
                          action, outcome, actor_type, target_type, target_id, metadata
                        ) VALUES (
                          'crm.recording.retention_delete', 'success', 'system',
                          'crm_recording', $1::uuid::text,
                          jsonb_build_object('private_object_deleted', true,
                                             'twilio_source_deleted', $2::boolean)
                        )
                        """,
                        row["id"], source_deleted,
                    )
            deleted += 1
        else:
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
                    await conn.execute(
                        """
                        UPDATE crm_recordings
                        SET status = 'error', error_code = $2,
                            source_deleted_at = CASE
                              WHEN $3 THEN COALESCE(source_deleted_at, NOW())
                              ELSE source_deleted_at
                            END,
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"], object_error, source_deleted,
                    )
                    await conn.execute(
                        """
                        INSERT INTO audit_log (
                          action, outcome, actor_type, target_type, target_id, metadata
                        ) VALUES (
                          'crm.recording.retention_delete', 'partial_failure', 'system',
                          'crm_recording', $1::uuid::text,
                          jsonb_build_object('private_object_deleted', false,
                                             'twilio_source_deleted', $2::boolean,
                                             'error_code', $3::text)
                        )
                        """,
                        row["id"], source_deleted, object_error,
                    )
            failed += 1
    return {"deleted": deleted, "failed": failed, "sources_deleted": sources_deleted}
