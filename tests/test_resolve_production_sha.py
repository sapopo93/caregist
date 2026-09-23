from __future__ import annotations

import pytest

from tools import resolve_production_sha as resolver


def _statuses(state: str) -> list[dict]:
    return [{"state": state}]


def test_picks_newest_successful_deployment_and_skips_newer_non_success():
    calls = []

    def fetch(path: str):
        calls.append(path)
        if path.startswith("/deployments?"):
            return [
                {"id": 3, "sha": "c" * 40},
                {"id": 2, "sha": "b" * 40},
                {"id": 1, "sha": "a" * 40},
            ]
        if path == "/deployments/3/statuses?per_page=1":
            return _statuses("in_progress")
        if path == "/deployments/2/statuses?per_page=1":
            return _statuses("failure")
        if path == "/deployments/1/statuses?per_page=1":
            return _statuses("success")
        raise AssertionError(f"unexpected path {path}")

    sha = resolver.resolve(fetch)

    assert sha == "a" * 40


def test_skips_inactive_and_returns_first_success_in_order():
    def fetch(path: str):
        if path.startswith("/deployments?"):
            return [
                {"id": 2, "sha": "b" * 40},
                {"id": 1, "sha": "a" * 40},
            ]
        if path == "/deployments/2/statuses?per_page=1":
            return _statuses("inactive")
        if path == "/deployments/1/statuses?per_page=1":
            return _statuses("success")
        raise AssertionError(f"unexpected path {path}")

    sha = resolver.resolve(fetch)

    assert sha == "a" * 40


def test_empty_deployment_list_raises():
    with pytest.raises(ValueError, match="no successful Production deployment"):
        resolver.resolve(lambda _path: [])


def test_no_successful_deployment_raises():
    def fetch(path: str):
        if path.startswith("/deployments?"):
            return [{"id": 1, "sha": "a" * 40}]
        return _statuses("failure")

    with pytest.raises(ValueError, match="no successful Production deployment"):
        resolver.resolve(fetch)


def test_malformed_sha_raises():
    def fetch(path: str):
        if path.startswith("/deployments?"):
            return [{"id": 1, "sha": "not-a-sha"}]
        return _statuses("success")

    with pytest.raises(ValueError, match="invalid sha"):
        resolver.resolve(fetch)


def test_http_error_propagates():
    def fetch(_path: str):
        raise OSError("boom")

    with pytest.raises(OSError):
        resolver.resolve(fetch)


def test_main_requires_env_vars(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    assert resolver.main() == 1
    assert "GITHUB_TOKEN" in capsys.readouterr().err


def test_main_prints_sha_and_exits_zero(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(
        resolver,
        "fetch_json",
        lambda url, *, token: [{"id": 1, "sha": "a" * 40}]
        if "/deployments?" in url
        else _statuses("success"),
    )

    assert resolver.main() == 0
    assert capsys.readouterr().out.strip() == "a" * 40


def test_main_fails_closed_on_resolve_error(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(resolver, "fetch_json", lambda url, *, token: [])

    assert resolver.main() == 1
    assert "resolve_production_sha" in capsys.readouterr().err
