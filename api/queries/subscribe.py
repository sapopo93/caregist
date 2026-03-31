"""SQL queries for email subscription endpoints."""

INSERT_SUBSCRIBER = """
INSERT INTO email_subscribers (email, source, postcode, meta)
VALUES ($1, $2, $3, $4::jsonb)
ON CONFLICT (email, source) DO NOTHING
RETURNING id, email, source, created_at
"""

GET_LAST_SYNC_DATE = """
SELECT completed_at
FROM pipeline_runs
WHERE status = 'completed' AND completed_at IS NOT NULL
ORDER BY completed_at DESC
LIMIT 1
"""
