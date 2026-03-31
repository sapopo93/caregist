"""SQL queries for saved comparisons."""

INSERT_COMPARISON = """
INSERT INTO saved_comparisons (user_id, share_token, slug_list, title)
VALUES ($1, $2, $3, $4)
RETURNING id, share_token, slug_list, title, created_at
"""

GET_BY_TOKEN = """
SELECT id, user_id, share_token, slug_list, title, created_at
FROM saved_comparisons
WHERE share_token = $1
"""

LIST_BY_USER = """
SELECT id, share_token, slug_list, title, created_at
FROM saved_comparisons
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 50
"""

COUNT_BY_USER = """
SELECT COUNT(*) as total FROM saved_comparisons WHERE user_id = $1
"""

DELETE_COMPARISON = """
DELETE FROM saved_comparisons WHERE id = $1 AND user_id = $2
"""
