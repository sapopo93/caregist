"""Application configuration via environment variables."""

from __future__ import annotations

import sys

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://caregist:caregist_dev@localhost:5432/caregist"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_master_key: str = "change_me_in_production"
    default_page_size: int = 20
    max_page_size: int = 100
    cors_origins: str = "http://localhost:3000"
    query_timeout_ms: int = 10000
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    app_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def validate_production(self) -> None:
        if self.api_master_key == "change_me_in_production":
            print("WARNING: API_MASTER_KEY is set to default. Set a secure value in .env", file=sys.stderr)


settings = Settings()
settings.validate_production()
