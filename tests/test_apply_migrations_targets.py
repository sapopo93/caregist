from __future__ import annotations

import asyncio
import sys
import types

import pytest

from db import apply_migrations


def test_resolve_database_url_requires_explicit_staging_target(monkeypatch):
    monkeypatch.delenv("STAGING_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="STAGING_DATABASE_URL"):
        apply_migrations.resolve_database_url(None, target="staging")


def test_resolve_database_url_uses_staging_target_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://prod.example/app")
    monkeypatch.setenv("STAGING_DATABASE_URL", "postgresql://staging.example/app")

    assert apply_migrations.resolve_database_url(None, target="staging") == "postgresql://staging.example/app"


def test_resolve_database_url_requires_production_backup_confirmation(monkeypatch):
    monkeypatch.setenv("PROD_DATABASE_URL", "postgresql://prod.example/app")

    with pytest.raises(RuntimeError, match="backup"):
        apply_migrations.resolve_database_url(None, target="production")

    assert (
        apply_migrations.resolve_database_url(None, target="production", confirm_production_backup=True)
        == "postgresql://prod.example/app"
    )


def test_read_only_check_needs_no_backup_assertion(monkeypatch):
    """--check mutates nothing, so it must not demand a restore-point claim."""
    monkeypatch.setenv("PROD_DATABASE_URL", "postgresql://prod.example/app")

    assert (
        apply_migrations.resolve_database_url(None, target="production", read_only=True)
        == "postgresql://prod.example/app"
    )


def test_read_only_check_still_requires_a_production_url(monkeypatch):
    monkeypatch.delenv("PROD_DATABASE_URL", raising=False)
    monkeypatch.setattr(apply_migrations, "_read_env_file_value", lambda name: None)

    with pytest.raises(RuntimeError, match="PROD_DATABASE_URL"):
        apply_migrations.resolve_database_url(None, target="production", read_only=True)


class _FakeConnection:
    """Stands in for an asyncpg connection and refuses any write."""

    def __init__(self, ledger: str | None, applied: list[str] | None = None):
        self._ledger = ledger
        self._applied = applied or []
        self.closed = False

    async def fetchval(self, query: str):
        assert query.strip().upper().startswith("SELECT"), "check mode must only read"
        return self._ledger

    async def fetch(self, query: str):
        assert query.strip().upper().startswith("SELECT"), "check mode must only read"
        return [{"filename": name} for name in self._applied]

    async def execute(self, *args, **kwargs):
        raise AssertionError("check mode must never write to the database")

    async def close(self):
        self.closed = True


def _install_fake_asyncpg(monkeypatch, conn: _FakeConnection):
    async def _connect(database_url: str):
        return conn

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=_connect))


@pytest.fixture
def migrations_dir(tmp_path, monkeypatch):
    for name in ("057_alpha.sql", "058_beta.sql", "059_gamma.sql"):
        (tmp_path / name).write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "down").mkdir()
    (tmp_path / "down" / "057_alpha_down.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "notes.md").write_text("not a migration", encoding="utf-8")
    monkeypatch.setattr(apply_migrations, "MIGRATIONS_DIR", tmp_path)
    return tmp_path


def test_pending_migrations_treats_missing_ledger_as_everything_pending(monkeypatch, migrations_dir):
    conn = _FakeConnection(ledger=None)
    _install_fake_asyncpg(monkeypatch, conn)

    pending = asyncio.run(apply_migrations.pending_migrations("postgresql://anywhere/db"))

    assert pending == ["057_alpha.sql", "058_beta.sql", "059_gamma.sql"]
    assert conn.closed is True


def test_pending_migrations_reports_only_unapplied_files(monkeypatch, migrations_dir):
    conn = _FakeConnection(ledger="schema_migrations", applied=["057_alpha.sql", "059_gamma.sql"])
    _install_fake_asyncpg(monkeypatch, conn)

    pending = asyncio.run(apply_migrations.pending_migrations("postgresql://anywhere/db"))

    assert pending == ["058_beta.sql"]
    assert conn.closed is True


def test_pending_migrations_ignores_down_migrations_and_non_sql(monkeypatch, migrations_dir):
    conn = _FakeConnection(ledger="schema_migrations", applied=["057_alpha.sql", "058_beta.sql", "059_gamma.sql"])
    _install_fake_asyncpg(monkeypatch, conn)

    assert asyncio.run(apply_migrations.pending_migrations("postgresql://anywhere/db")) == []


@pytest.mark.parametrize(
    "pending, expected_exit",
    [([], 0), (["064_delta.sql"], 1)],
)
def test_main_check_exit_code_follows_drift(monkeypatch, pending, expected_exit):
    monkeypatch.setenv("PROD_DATABASE_URL", "postgresql://prod.example/app")
    monkeypatch.setattr(sys, "argv", ["apply_migrations.py", "--target", "production", "--check"])

    async def _fake_pending(database_url: str):
        return list(pending)

    monkeypatch.setattr(apply_migrations, "pending_migrations", _fake_pending)

    assert apply_migrations.main() == expected_exit
