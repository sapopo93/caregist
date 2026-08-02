#!/usr/bin/env python3

import json
import os
import sys
import time
from dataclasses import dataclass
from html import unescape
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Response:
    status: int
    headers: Mapping[str, str]
    body: str


class SmokeFailure(RuntimeError):
    pass


BASE_URL = os.getenv("CAREGIST_APP_URL", "https://www.caregist.co.uk").rstrip("/")
SEARCH_QUERY = os.getenv("CAREGIST_SEARCH_QUERY", "East London")
SERVICE_TYPE = os.getenv("CAREGIST_SERVICE_TYPE", "Homecare Agencies")
EXPECTED_PROVIDER = os.getenv("CAREGIST_EXPECTED_PROVIDER", "London Care (East London)")
PROVIDER_SLUG = os.getenv("CAREGIST_PROVIDER_SLUG", "london-care-east-london-london")
EXPORT_TOKEN = os.getenv("CAREGIST_EXPORT_TOKEN", "").strip()
LEAD_EMAIL = os.getenv("CAREGIST_LEAD_EMAIL", "").strip()
REGION = os.getenv("CAREGIST_REGION", "").strip()
RATING = os.getenv("CAREGIST_RATING", "").strip()
TIMEOUT_SECONDS = float(os.getenv("CAREGIST_SMOKE_TIMEOUT_SECONDS", "20"))
ATTEMPTS = max(1, int(os.getenv("CAREGIST_SMOKE_ATTEMPTS", "1")))
RETRY_DELAY_SECONDS = max(0.0, float(os.getenv("CAREGIST_SMOKE_RETRY_DELAY_SECONDS", "10")))
REQUIRE_DATABASE = os.getenv("CAREGIST_REQUIRE_DATABASE", "").strip().lower() in {"1", "true", "yes"}
EXPECTED_GIT_SHA = os.getenv("CAREGIST_EXPECTED_GIT_SHA", "").strip().lower()
SKIP_BACKEND_PATHS = os.getenv("CAREGIST_SKIP_BACKEND_PATHS", "").strip().lower() in {"1", "true", "yes"}
VERCEL_AUTOMATION_BYPASS_SECRET = os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET", "").strip()

REDIRECT_OPENER = build_opener(NoRedirectHandler)


def fetch(path: str, *, method: str = "GET", data: bytes | None = None, headers: dict[str, str] | None = None) -> Response:
    request_headers = dict(headers or {})
    if VERCEL_AUTOMATION_BYPASS_SECRET:
        request_headers["x-vercel-protection-bypass"] = VERCEL_AUTOMATION_BYPASS_SECRET
    request = Request(
        urljoin(f"{BASE_URL}/", path.lstrip("/")),
        data=data,
        headers=request_headers,
        method=method,
    )

    try:
        with REDIRECT_OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
            return Response(
                status=response.status,
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read().decode("utf-8", "replace"),
            )
    except HTTPError as error:
        return Response(
            status=error.code,
            headers={key.lower(): value for key, value in error.headers.items()},
            body=error.read().decode("utf-8", "replace"),
        )
    except URLError as error:
        raise SmokeFailure(f"request to {request.full_url} failed: {error.reason}") from error


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def print_ok(label: str, detail: str) -> None:
    print(f"{label}: OK - {detail}")


def response_diagnostic(response: Response) -> str:
    body = " ".join(response.body.split())[:300]
    request_id = response.headers.get("x-request-id") or response.headers.get("x-vercel-id") or "missing"
    return f"HTTP {response.status}; requestId={request_id}; body={body!r}"


def verify_health() -> None:
    response = fetch("/api/health/directory")
    assert_true(response.status == 200, f"/api/health/directory failed: {response_diagnostic(response)}")

    try:
      payload = json.loads(response.body)
    except json.JSONDecodeError as error:
      raise SmokeFailure(f"/api/health/directory returned invalid JSON: {error}") from error

    capabilities = payload.get("capabilities") or {}
    status = payload.get("status")
    operating_mode = capabilities.get("operatingMode")
    read_mode = capabilities.get("readMode")
    write_mode = capabilities.get("writeMode")
    notification_mode = capabilities.get("notificationMode")
    database_available = capabilities.get("databaseAvailable")
    database_reason = capabilities.get("databaseReason")
    release_git_sha = str((payload.get("release") or {}).get("gitSha") or "").lower()

    assert_true(status in {"ok", "degraded"}, f"health status was {status!r}")
    assert_true(operating_mode in {"database", "fallback"}, f"unexpected operatingMode {operating_mode!r}")
    assert_true(read_mode in {"database", "full-dataset-fallback"}, f"unexpected readMode {read_mode!r}")
    assert_true(write_mode in {"database", "stateless-token"}, f"unexpected writeMode {write_mode!r}")
    assert_true(notification_mode in {"email", "log-only"}, f"unexpected notificationMode {notification_mode!r}")
    if EXPECTED_GIT_SHA:
        assert_true(
            release_git_sha == EXPECTED_GIT_SHA,
            f"deployed Git SHA {release_git_sha!r} did not match tested SHA {EXPECTED_GIT_SHA!r}",
        )

    if REQUIRE_DATABASE:
        assert_true(database_available is True, f"databaseAvailable was {database_available!r} ({database_reason})")
        assert_true(read_mode == "database", f"readMode was {read_mode!r}")
        assert_true(write_mode == "database", f"writeMode was {write_mode!r}")

    print_ok(
        "HEALTH",
        " ".join(
            [
                f"status={status}",
                f"operatingMode={operating_mode}",
                f"readMode={read_mode}",
                f"writeMode={write_mode}",
                f"notificationMode={notification_mode}",
                f"databaseReason={database_reason}",
                f"gitSha={release_git_sha or 'missing'}",
            ]
        ),
    )


def verify_data_status() -> None:
    response = fetch("/data-status")
    assert_true(response.status == 200, f"/data-status failed: {response_diagnostic(response)}")
    assert_true("data status" in unescape(response.body).lower(), "/data-status did not render its status heading")
    print_ok("DATA_STATUS", "/data-status rendered")


def verify_backend_binding() -> None:
    response = fetch("/api/v1/health/freshness")
    assert_true(
        response.status in {200, 503},
        f"backend freshness binding failed: {response_diagnostic(response)}",
    )
    try:
        payload = json.loads(response.body)
    except json.JSONDecodeError as error:
        raise SmokeFailure(f"backend freshness binding returned invalid JSON: {error}") from error

    status = payload.get("status")
    assert_true(status in {"healthy", "stale"}, f"backend freshness returned unexpected status {status!r}")
    backend_sha = str((payload.get("release") or {}).get("git_sha") or "").lower()
    if EXPECTED_GIT_SHA:
        assert_true(
            backend_sha == EXPECTED_GIT_SHA,
            f"backend Git SHA {backend_sha!r} did not match tested SHA {EXPECTED_GIT_SHA!r}",
        )
    print_ok("BACKEND_BINDING", f"freshnessStatus={status} gitSha={backend_sha or 'missing'}")


def verify_provider_sitemap() -> None:
    response = fetch("/provider-sitemap-index.xml")
    assert_true(response.status == 200, f"provider sitemap failed: {response_diagnostic(response)}")
    content_type = response.headers.get("content-type", "")
    assert_true("xml" in content_type, f"provider sitemap returned unexpected Content-Type {content_type!r}")
    assert_true("<sitemapindex" in response.body, "provider sitemap response did not contain a sitemap index")
    print_ok("PROVIDER_SITEMAP", "provider sitemap index rendered")


def verify_search() -> None:
    response = fetch(f"/search?{urlencode({'q': SEARCH_QUERY, 'service_type': SERVICE_TYPE})}")
    assert_true(response.status == 200, f"/search returned HTTP {response.status}")
    body = unescape(response.body)

    assert_true("temporarily unavailable" not in body, "search rendered the temporary-unavailable fallback")
    assert_true("No matching providers found" not in body, "search returned an empty result set")
    assert_true(EXPECTED_PROVIDER in body, f"search did not include expected provider {EXPECTED_PROVIDER!r}")

    print_ok("SEARCH", f"found {EXPECTED_PROVIDER!r} for q={SEARCH_QUERY!r} service_type={SERVICE_TYPE!r}")


def verify_provider_page() -> None:
    response = fetch(f"/provider/{PROVIDER_SLUG}")
    assert_true(response.status == 200, f"/provider/{PROVIDER_SLUG} returned HTTP {response.status}")
    body = unescape(response.body)

    assert_true("temporarily unavailable" not in body, "provider page rendered the temporary-unavailable state")
    assert_true(EXPECTED_PROVIDER in body, f"provider page did not include expected provider {EXPECTED_PROVIDER!r}")
    assert_true("<title>" in body and EXPECTED_PROVIDER in body, "provider page title/body did not include the expected provider")

    print_ok("PROVIDER", f"/provider/{PROVIDER_SLUG} rendered {EXPECTED_PROVIDER!r}")


def verify_export_requires_token() -> bool:
    response = fetch("/api/export")
    if response.status == 503:
        assert_true(
            "Human Gate" in response.body or "awaiting" in response.body,
            "disabled export response did not explain the governance gate",
        )
        print_ok("EXPORT_GUARD", "export delivery is fail-closed with HTTP 503")
        return False
    assert_true(response.status == 401, f"/api/export without token returned HTTP {response.status}")
    assert_true("Export token required" in response.body, "unauthenticated export response did not explain the token requirement")

    print_ok("EXPORT_GUARD", "anonymous export access is blocked with HTTP 401")
    return True


def verify_export_with_token(token: str) -> None:
    query = {"token": token}
    if REGION:
        query["region"] = REGION
    if SERVICE_TYPE:
        query["service_type"] = SERVICE_TYPE
    if RATING:
        query["rating"] = RATING

    response = fetch(f"/api/export?{urlencode(query)}")
    assert_true(response.status == 200, f"/api/export with token returned HTTP {response.status}")
    content_type = response.headers.get("content-type", "")
    assert_true("text/csv" in content_type, f"/api/export returned unexpected Content-Type {content_type!r}")
    assert_true(
        "name,slug,region,service_types,specialisms,phone,website,overall_rating,registration_date,inspection_report_url,source_attribution"
        in response.body,
        "export CSV header was missing or changed",
    )
    assert_true(EXPECTED_PROVIDER in response.body, f"export CSV did not include expected provider {EXPECTED_PROVIDER!r}")

    print_ok("EXPORT", f"token-gated CSV export returned rows for {EXPECTED_PROVIDER!r}")


def verify_lead_capture_and_export() -> None:
    form = urlencode(
        {
            "email": LEAD_EMAIL,
            "region": REGION,
            "service_type": SERVICE_TYPE,
            "rating": RATING,
        }
    ).encode("utf-8")

    response = fetch(
        "/api/leads/request",
        method="POST",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status == 503:
        assert_true(
            "Human Gate" in response.body or "awaiting" in response.body,
            "disabled lead response did not explain the governance gate",
        )
        print_ok("LEAD_GUARD", "lead intake is fail-closed with HTTP 503")
        return
    assert_true(response.status == 303, f"/api/leads/request returned HTTP {response.status}")
    location = response.headers.get("location", "")
    assert_true(location, "lead request redirect did not include a Location header")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    if response.status == 303 and (params.get("hold") or [""])[0] == "human-gate":
        assert_true(parsed.path == "/lead-list", f"lead hold redirected to unexpected path {parsed.path!r}")
        print_ok("LEAD_GUARD", "lead intake is fail-closed behind the Human Gate redirect")
        return
    token = (params.get("token") or [""])[0]
    mode = (params.get("mode") or [""])[0]

    assert_true(parsed.path == "/lead-list", f"lead request redirected to unexpected path {parsed.path!r}")
    assert_true((params.get("submitted") or [""])[0] == "1", "lead request redirect did not mark the submission as successful")
    assert_true(mode in {"database", "stateless"}, f"lead request redirect returned unexpected mode {mode!r}")
    assert_true(bool(token), "lead request redirect did not include an export token")

    print_ok("LEAD", f"lead capture redirected with mode={mode} and issued an export token")
    verify_export_with_token(token)


def main() -> int:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            verify_health()
            verify_data_status()
            if SKIP_BACKEND_PATHS:
                print("BACKEND_BINDING: SKIPPED - frontend-only degraded smoke has no backend service")
                print("PROVIDER_SITEMAP: SKIPPED - frontend-only degraded smoke has no backend service")
            else:
                verify_backend_binding()
                verify_provider_sitemap()
            verify_search()
            verify_provider_page()
            exports_enabled = verify_export_requires_token()

            if LEAD_EMAIL:
                verify_lead_capture_and_export()
            elif EXPORT_TOKEN and exports_enabled:
                verify_export_with_token(EXPORT_TOKEN)
            elif not exports_enabled:
                print("EXPORT: SKIPPED - delivery is governance-gated")
            else:
                print("EXPORT: SKIPPED - set CAREGIST_LEAD_EMAIL for a full lead/export smoke, or CAREGIST_EXPORT_TOKEN to verify a pre-issued token")

            return 0
        except SmokeFailure as error:
            if attempt >= ATTEMPTS:
                print(f"SMOKE FAILED: {error}", file=sys.stderr)
                return 1

            print(
                f"SMOKE RETRY {attempt}/{ATTEMPTS - 1}: {error}. Retrying in {RETRY_DELAY_SECONDS:.1f}s...",
                file=sys.stderr,
            )
            time.sleep(RETRY_DELAY_SECONDS)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
