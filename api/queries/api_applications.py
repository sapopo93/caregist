"""SQL queries for API applications."""

INSERT_APPLICATION = """
INSERT INTO api_applications (company_name, contact_name, contact_email, use_case, expected_volume)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, company_name, contact_email, status, created_at
"""
