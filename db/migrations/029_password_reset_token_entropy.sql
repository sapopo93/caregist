-- Password reset tokens are now high-entropy urlsafe tokens, not six-digit codes.

ALTER TABLE password_reset_tokens
    ALTER COLUMN token TYPE TEXT;
