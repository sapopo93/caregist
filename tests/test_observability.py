from copy import deepcopy
from unittest.mock import MagicMock

from api.observability import configure_sentry, scrub_error_event


def test_customer_content_is_withheld_but_stack_location_remains():
    event = {
        "event_id": "receipt", "environment": "production",
        "request": {"data": "private enquiry", "headers": {"Authorization": "secret"}},
        "user": {"email": "person@example.com"}, "extra": {"payment": "private"},
        "contexts": {"customer": "private"}, "tags": {"org": "private"},
        "transaction": "/customers/private", "server_name": "private-host",
        "breadcrumbs": [{"message": "secret"}], "message": "secret",
        "logentry": {"formatted": "secret"},
        "exception": {"values": [{"type": "ValueError", "value": "secret",
            "mechanism": {"data": {"password": "secret"}},
            "stacktrace": {"frames": [{"filename": "api/example.py", "lineno": 42,
                "vars": {"secret": "secret"}}]}}]},
    }
    cleaned = scrub_error_event(deepcopy(event), {})
    assert "secret" not in str(cleaned) and "private" not in str(cleaned)
    assert cleaned["exception"]["values"][0]["type"] == "ValueError"
    assert cleaned["exception"]["values"][0]["stacktrace"]["frames"] == [
        {"filename": "api/example.py", "lineno": 42}]
    assert cleaned["event_id"] == "receipt"


def test_no_dsn_or_sdk_does_not_initialise():
    sdk = MagicMock()
    assert not configure_sentry(sdk, "", production=True)
    sdk.init.assert_not_called()
    assert not configure_sentry(None, "configured", production=True)


def test_sdk_uses_error_only_configuration_without_rollout_event(monkeypatch):
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "abc")
    monkeypatch.delenv("SENTRY_VERIFY_RELEASE", raising=False)
    sdk = MagicMock()
    assert configure_sentry(sdk, "configured", production=True)
    options = sdk.init.call_args.kwargs
    assert options["before_send"] is scrub_error_event
    assert options["send_default_pii"] is False
    assert options["include_local_variables"] is False
    assert options["max_request_body_size"] == "never"
    assert options["traces_sample_rate"] == options["profiles_sample_rate"] == 0
    assert options["enable_logs"] is False
    assert options["release"] == "caregist-api@abc"
    sdk.capture_exception.assert_not_called()


def test_rollout_receipt_requires_production_and_exact_release(monkeypatch):
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "abc")
    monkeypatch.setenv("SENTRY_VERIFY_RELEASE", "other")
    sdk = MagicMock()
    configure_sentry(sdk, "configured", production=True)
    sdk.capture_exception.assert_not_called()
    monkeypatch.setenv("SENTRY_VERIFY_RELEASE", "abc")
    configure_sentry(sdk, "configured", production=False)
    sdk.capture_exception.assert_not_called()
    configure_sentry(sdk, "configured", production=True)
    assert sdk.capture_exception.call_args.args[0].__class__.__name__ == "CareGistSentryVerification"
    assert sdk.new_scope.return_value.__enter__.return_value.level == "info"
    sdk.flush.assert_called_once_with(timeout=2)
