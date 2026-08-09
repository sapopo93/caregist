from __future__ import annotations

import pytest

from db.apply_migrations import resolve_database_url


def test_resolve_database_url_requires_explicit_staging_target(monkeypatch):
    monkeypatch.delenv("STAGING_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="STAGING_DATABASE_URL"):
        resolve_database_url(None, target="staging")


def test_resolve_database_url_uses_staging_target_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://prod.example/app")
    monkeypatch.setenv("STAGING_DATABASE_URL", "postgresql://staging.example/app")

    assert resolve_database_url(None, target="staging") == "postgresql://staging.example/app"


def test_resolve_database_url_requires_production_backup_confirmation(monkeypatch):
    monkeypatch.setenv("PROD_DATABASE_URL", "postgresql://prod.example/app")

    with pytest.raises(RuntimeError, match="backup"):
        resolve_database_url(None, target="production")

    assert (
        resolve_database_url(None, target="production", confirm_production_backup=True)
        == "postgresql://prod.example/app"
    )
