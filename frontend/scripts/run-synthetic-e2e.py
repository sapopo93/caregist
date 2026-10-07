#!/usr/bin/env python3
"""Run browser workflows against a fresh, loopback-only synthetic CareGist DB."""

from __future__ import annotations

import asyncio
import getpass
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import asyncpg

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
RUN_ID = f"{os.getpid()}_{secrets.token_hex(3)}"
DB_NAME = f"caregist_workflow_{RUN_ID}"
ROLE_NAME = f"caregist_wf_{RUN_ID}"
PASSWORD = secrets.token_urlsafe(32)
MASTER_KEY = f"workflow_synthetic_{secrets.token_urlsafe(24)}"
FRONTEND_PORT = int(os.getenv("CAREGIST_SYNTHETIC_FRONTEND_PORT", "18111"))
BACKEND_PORT = int(os.getenv("CAREGIST_SYNTHETIC_BACKEND_PORT", "18112"))
ADMIN_URL = os.getenv(
    "CAREGIST_SYNTHETIC_ADMIN_URL",
    f"postgresql://{quote(getpass.getuser(), safe='')}@localhost:5432/postgres",
)
AUDIT_DIR = Path(os.getenv(
    "CAREGIST_AUDIT_OUTPUT",
    "/Users/user/caregist-CareOps/audits/2026-10-06/caregist-workflow-review",
))
RESOURCES_CREATED = False


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def local_url() -> str:
    parsed = urlparse(ADMIN_URL)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Synthetic browser DB must be on a loopback PostgreSQL host.")
    return ADMIN_URL


def assert_ports_free() -> None:
    for port in (FRONTEND_PORT, BACKEND_PORT):
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Loopback port {port} is already occupied; refusing to reuse a service.")


async def provision() -> tuple[str, str, int, bool]:
    global RESOURCES_CREATED
    admin = await asyncpg.connect(local_url())
    try:
        if await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME):
            raise RuntimeError(f"Refusing to overwrite existing database {DB_NAME}.")
        if await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", ROLE_NAME):
            raise RuntimeError(f"Refusing to overwrite existing role {ROLE_NAME}.")
        await admin.execute(
            f'CREATE ROLE "{ROLE_NAME}" LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD \'{PASSWORD}\''
        )
        try:
            await admin.execute(
                f'CREATE DATABASE "{DB_NAME}" OWNER "{ROLE_NAME}" ENCODING \'UTF8\' TEMPLATE template0'
            )
        except Exception:
            await admin.execute(f'DROP ROLE IF EXISTS "{ROLE_NAME}"')
            raise
        RESOURCES_CREATED = True
    finally:
        await admin.close()

    admin_parsed = urlparse(ADMIN_URL)
    # The app's local-runtime guard explicitly recognizes localhost. The
    # PostgreSQL cluster still binds only loopback; no remote host is used.
    host = "localhost"
    port = admin_parsed.port or 5432
    admin_db_url = f"postgresql://{quote(admin_parsed.username or getpass.getuser(), safe='')}@{host}:{port}/{DB_NAME}"
    try:
        admin = await asyncpg.connect(admin_db_url)
        try:
            extension_available = bool(await admin.fetchval("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'"))
            if extension_available:
                await admin.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        finally:
            await admin.close()

        db_url = f"postgresql://{quote(ROLE_NAME, safe='')}:{quote(PASSWORD, safe='')}@{host}:{port}/{DB_NAME}"
        sys.path.insert(0, str(ROOT))
        from tests.integration.conftest import apply_full_schema, postgis_available

        conn = await asyncpg.connect(db_url)
        try:
            has_postgis = await postgis_available(conn)
            applied = await apply_full_schema(conn)
            await seed_fixture_data(conn, has_postgis)
        finally:
            await conn.close()
    except Exception:
        await cleanup(DB_NAME, ROLE_NAME)
        RESOURCES_CREATED = False
        raise
    return db_url, ROLE_NAME, len(applied), has_postgis


async def seed_fixture_data(conn: asyncpg.Connection, has_postgis: bool) -> None:
    # Forty-five obviously synthetic records are enough to exercise filters,
    # pagination, profiles, compare, and a stale territory coverage result.
    for index in range(1, 46):
        region = "London" if index <= 30 else "North West"
        rating = "Inadequate"
        slug = f"synthetic-workflow-provider-{index:02d}"
        await conn.execute(
            """INSERT INTO care_providers (
                 id, provider_id, name, slug, type, status, registration_date,
                 address_line1, town, county, postcode, region, local_authority,
                 latitude, longitude, overall_rating, rating_safe, rating_effective,
                 rating_caring, rating_responsive, rating_well_led,
                 last_inspection_date, inspection_report_url, service_types,
                 specialisms, number_of_beds, ownership_type, data_completeness_score
               ) VALUES (
                 $1, $2, $3, $4, 'Social Care Org', 'ACTIVE', DATE '2020-01-01',
                 '1 Synthetic Street', 'Testville', $5, 'SW1A 1AA', $6, 'Test Borough',
                 51.5014, -0.1419, $7, $7, $7, $7, $7, $7,
                 DATE '2020-02-01', $8,
                 'Homecare Agencies', 'Synthetic test fixture', 0, 'Synthetic fixture', 100
               )""",
            f"SYN-WF-{index:04d}",
            f"SYN-PROV-{index:04d}",
            f"Synthetic Workflow Care {index:02d}",
            slug,
            "Synthetic County",
            region,
            rating,
            f"https://www.cqc.org.uk/location/SYN-WF-{index:04d}",
        )

    if has_postgis:
        await conn.execute(
            """UPDATE care_providers SET geom = ST_SetSRID(ST_MakePoint(-0.1419, 51.5014), 4326)
               WHERE id LIKE 'SYN-WF-%'"""
        )

    # Create a real verified owner account and a separate unverified signup path.
    import bcrypt
    from hashlib import sha256

    email = "workflow-owner@example.com"
    password = "Synthetic-Workflow-2026!"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = await conn.fetchval(
        """INSERT INTO users (email, name, password_hash, is_verified)
           VALUES ($1, 'Synthetic Workflow Owner', $2, TRUE) RETURNING id""",
        email,
        password_hash,
    )
    user_key = f"cg_{secrets.token_urlsafe(32)}"
    await conn.fetchval(
        """INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
           VALUES ($1, $2, 'Synthetic E2E owner', $3, 'free', 100, TRUE, $4) RETURNING id""",
        sha256(user_key.encode()).hexdigest(),
        user_key[:10],
        email,
        user_id,
    )
    await conn.execute(
        """INSERT INTO subscriptions (user_id, tier, status) VALUES ($1, 'free', 'active')""",
        user_id,
    )
    org_id = await conn.fetchval(
        """INSERT INTO organizations (name, slug, created_by_user_id)
           VALUES ('Synthetic Workflow Organization', 'synthetic-workflow', $1)
           RETURNING id""",
        user_id,
    )
    await conn.execute(
        "INSERT INTO organization_members (organization_id, user_id, role) VALUES ($1, $2, 'owner')",
        org_id,
        user_id,
    )
    await conn.execute("SELECT set_config('caregist.user_id', $1, false)", str(user_id))
    contact_id = await conn.fetchval(
        """INSERT INTO crm_contacts (
             organization_id, provider_id, owner_user_id, created_by_user_id,
             first_name, last_name, job_title, company_name, email
           ) VALUES ($1, 'SYN-WF-0001', $2, $2, 'Synthetic', 'Operator',
             'Care Manager', 'Synthetic Care Group', 'contact@example.com')
           RETURNING id""",
        org_id,
        user_id,
    )
    claim_id = await conn.fetchval(
        """INSERT INTO provider_claims (
             provider_id, claimant_name, claimant_email, claimant_role, organisation_name
           ) VALUES ('SYN-WF-0001', 'Synthetic Claimant', 'claimant@example.com',
             'Synthetic test role', 'Synthetic Test Organisation') RETURNING id"""
    )
    review_id = await conn.fetchval(
        """INSERT INTO reviews (
             provider_id, rating, title, body, reviewer_name, reviewer_email, relationship
           ) VALUES ('SYN-WF-0001', 4, 'Synthetic test review', 'Synthetic moderation fixture.',
             'Synthetic Reviewer', 'reviewer@example.com', 'Synthetic test only') RETURNING id"""
    )
    enquiry_id = await conn.fetchval(
        """INSERT INTO enquiries (
             provider_id, enquirer_name, enquirer_email, relationship, care_type, urgency, message
           ) VALUES ('SYN-WF-0001', 'Synthetic Enquirer', 'enquirer@example.com',
             'Synthetic test only', 'Synthetic fixture', 'exploring', 'Synthetic admin review test.')
           RETURNING id"""
    )
    lead_id = await conn.fetchval(
        """INSERT INTO leads (email, region, service_type, rating)
           VALUES ('export-entitlement@example.com', 'London', 'home-care', 'Inadequate')
           RETURNING id"""
    )
    await conn.execute(
        """INSERT INTO export_access_tokens (token, lead_id, region, service_type, rating, expires_at)
           VALUES ('synthetic-export-entitled-token', $1, 'London', 'home-care', 'Inadequate',
             NOW() + INTERVAL '1 day')""",
        lead_id,
    )
    await conn.execute(
        """INSERT INTO postcode_cache (postcode, latitude, longitude)
           VALUES ('SW1A1AA', 51.5014, -0.1419)
           ON CONFLICT (postcode) DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude"""
    )

    write_json(AUDIT_DIR / "fixture-identities.json", {
        "database": DB_NAME,
        "role": ROLE_NAME,
        "synthetic_user_email": email,
        "synthetic_organization_id": str(org_id),
        "synthetic_contact_id": str(contact_id),
        "synthetic_claim_id": claim_id,
        "synthetic_review_id": review_id,
        "synthetic_enquiry_id": enquiry_id,
        "provider_rows": 45,
        "master_key": "intentionally_not_persisted",
    })


async def wait_http(url: str, process: subprocess.Popen, log_name: str) -> None:
    import urllib.request

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{log_name} stopped during startup (exit {process.returncode}).")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for loopback {log_name} at {url}.")


async def cleanup(db_name: str, role_name: str) -> None:
    admin = await asyncpg.connect(local_url())
    try:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
            db_name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await admin.execute(f'DROP ROLE IF EXISTS "{role_name}"')
    finally:
        await admin.close()


async def read_persistence_evidence(db_url: str) -> dict[str, int]:
    conn = await asyncpg.connect(db_url)
    try:
        # The application role is subject to CRM row-level security. Verify
        # persisted CRM writes as the synthetic owner rather than mistaking
        # an intentionally invisible tenant row for a missing write.
        owner_id = await conn.fetchval("SELECT id FROM users WHERE email = 'workflow-owner@example.com'")
        if owner_id is not None:
            await conn.execute("SELECT set_config('caregist.user_id', $1, false)", str(owner_id))
        return {
            "synthetic_providers": await conn.fetchval("SELECT COUNT(*) FROM care_providers WHERE id LIKE 'SYN-WF-%'"),
            "signup_rows": await conn.fetchval("SELECT COUNT(*) FROM users WHERE email = 'browser-signup@example.com' AND is_verified = FALSE"),
            "crm_task_rows": await conn.fetchval("SELECT COUNT(*) FROM crm_tasks WHERE title = 'Synthetic browser workflow follow-up'"),
            "rejected_claims": await conn.fetchval("SELECT COUNT(*) FROM provider_claims WHERE claimant_email = 'claimant@example.com' AND status = 'rejected'"),
            "rejected_reviews": await conn.fetchval("SELECT COUNT(*) FROM reviews WHERE reviewer_email = 'reviewer@example.com' AND status = 'rejected'"),
            "read_enquiries": await conn.fetchval("SELECT COUNT(*) FROM enquiries WHERE enquirer_email = 'enquirer@example.com' AND status = 'read'"),
            "api_applications": await conn.fetchval("SELECT COUNT(*) FROM api_applications WHERE contact_email = 'api-interest@example.com'"),
            "queued_synthetic_emails": await conn.fetchval("SELECT COUNT(*) FROM pending_emails WHERE to_email LIKE '%@example.com' AND status = 'pending'"),
        }
    finally:
        await conn.close()


async def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    assert_ports_free()
    db_url = None
    backend = frontend = None
    backend_log = (AUDIT_DIR / "synthetic-backend.log").open("w", encoding="utf-8")
    frontend_log = (AUDIT_DIR / "synthetic-frontend.log").open("w", encoding="utf-8")
    test_log = (AUDIT_DIR / "synthetic-playwright.log").open("w+", encoding="utf-8")
    try:
        db_url, role_name, migration_count, has_postgis = await provision()
        # Child processes receive a small runtime-only environment. In
        # particular, never forward ambient cloud, model, payment, database,
        # or messaging credentials from the shell that launched this harness.
        safe_runtime_keys = (
            "PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "TMP", "TEMP",
            "LANG", "LC_ALL", "TZ", "TERM", "NO_COLOR", "FORCE_COLOR",
        )
        base_env = {key: os.environ[key] for key in safe_runtime_keys if key in os.environ}
        # Next and Pydantic may parse env files themselves. Shadow every
        # discovered key with an empty process value before adding the explicit
        # synthetic allowlist below, so credentials from local env files stay
        # inert in both runtimes.
        for env_file in (ROOT / ".env", ROOT / ".env.local", FRONTEND / ".env.local"):
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line and not line.startswith("#") and "=" in line:
                        base_env[line.split("=", 1)[0]] = ""
        locked_env = {
            "DATABASE_URL": db_url,
            "POSTGRES_URL": db_url,
            "API_MASTER_KEY": MASTER_KEY,
            "API_KEY": MASTER_KEY,
            "APP_URL": f"http://127.0.0.1:{FRONTEND_PORT}",
            "CORS_ORIGINS": f"http://127.0.0.1:{FRONTEND_PORT}",
            "API_URL": f"http://127.0.0.1:{BACKEND_PORT}",
            "NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{BACKEND_PORT}",
            "CAREGIST_BACKEND_URL": f"http://127.0.0.1:{BACKEND_PORT}",
            "CAREGIST_BACKEND_API_KEY": MASTER_KEY,
            "BILLING_CHECKOUT_ENABLED": "false",
            "OUTBOUND_COMMUNICATIONS_ENABLED": "false",
            "OUTBOUND_DELIVERY_ENABLED": "false",
            # A synthetic entitlement exercises the real local export handler;
            # checkout and every external money/delivery adapter stay off.
            "DIRECTORY_EXPORT_DELIVERY_ENABLED": "true",
            "FULL_DATASET_CHECKOUT_ENABLED": "true",
            "TERRITORY_SELF_SERVE_CHECKOUT_ENABLED": "false",
            "RADAR_CHECKOUT_ENABLED": "false",
            "RADAR_DELIVERY_ENABLED": "false",
            "CRM_ENABLED": "true",
            "CRM_CALLING_ENABLED": "false",
            "CRM_RECORDING_ENABLED": "false",
            "CRM_EMAIL_CAMPAIGNS_ENABLED": "false",
            "CRM_AI_ENABLED": "false",
            "RESEND_API_KEY": "",
            "RESEND_WEBHOOK_SECRET": "",
            "SUPPORT_INTERNAL_TOKEN": "workflow-synthetic-only",
            "CAREGIST_TO_SUPPORT_TOKEN": "",
            "WEBHOOK_SECRET_KEY": "",
            "REDIS_URL": "",
            "CQC_API_KEY": "",
            "VERCEL_TOKEN": "",
            "VERCEL_OIDC_TOKEN": "",
            "SENTRY_AUTH_TOKEN": "",
            "SENTRY_DSN": "",
            "STRIPE_SECRET_KEY": "",
            "STRIPE_WEBHOOK_SECRET": "",
            "STRIPE_PRICE_TERRITORY_BRIEF": "",
            "BLOB_READ_WRITE_TOKEN": "",
            "TWILIO_ACCOUNT_SID": "",
            "TWILIO_API_KEY_SID": "",
            "TWILIO_API_KEY_SECRET": "",
            "TWILIO_AUTH_TOKEN": "",
            "CAREGIST_SYNTHETIC_LOCAL_RUN": "1",
        }
        base_env.update(locked_env)
        write_json(AUDIT_DIR / "synthetic-environment.json", {
            "frontend": f"http://127.0.0.1:{FRONTEND_PORT}",
            "backend": f"http://127.0.0.1:{BACKEND_PORT}",
            "database": DB_NAME,
            "database_role": role_name,
            "migrations_applied": migration_count,
            "postgis_available": has_postgis,
            "billing_checkout_enabled": False,
            "outbound_communications_enabled": False,
            "outbound_delivery_enabled": False,
            "stripe_resend_blob_twilio_credentials": "blank in subprocess environment",
        })

        python = str(ROOT / ".venv/bin/python")
        backend = subprocess.Popen(
            [python, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
            cwd=ROOT,
            env=base_env,
            stdout=backend_log,
            stderr=subprocess.STDOUT,
        )
        await wait_http(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health", backend, "backend")
        frontend = subprocess.Popen(
            ["node", "node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", str(FRONTEND_PORT)],
            cwd=FRONTEND,
            env=base_env,
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
        )
        await wait_http(f"http://127.0.0.1:{FRONTEND_PORT}/api/health/directory", frontend, "frontend")
        e2e_env = base_env.copy()
        e2e_env["CAREGIST_SYNTHETIC_BASE_URL"] = f"http://127.0.0.1:{FRONTEND_PORT}"
        e2e_env["CAREGIST_SYNTHETIC_POSTGIS_AVAILABLE"] = "1" if has_postgis else "0"
        e2e_env["CAREGIST_SYNTHETIC_OWNER_EMAIL"] = "workflow-owner@example.com"
        e2e_env["CAREGIST_SYNTHETIC_OWNER_PASSWORD"] = "Synthetic-Workflow-2026!"
        if os.getenv("CAREGIST_SYNTHETIC_GREP"):
            e2e_env["CAREGIST_SYNTHETIC_GREP"] = os.environ["CAREGIST_SYNTHETIC_GREP"]
        command = ["npm", "exec", "--", "playwright", "test", "--config=playwright.synthetic.config.ts"]
        if e2e_env.get("CAREGIST_SYNTHETIC_GREP"):
            command.extend(["--grep", e2e_env["CAREGIST_SYNTHETIC_GREP"]])
        result = subprocess.run(command, cwd=FRONTEND, env=e2e_env, stdout=test_log, stderr=subprocess.STDOUT)
        test_log.flush()
        test_log.seek(0)
        print(test_log.read())
        summary = {
            "database": DB_NAME,
            "role": ROLE_NAME,
            "migrations_applied": migration_count,
            "postgis_available": has_postgis,
            "playwright_exit_code": result.returncode,
            "db_persistence": await read_persistence_evidence(db_url),
            "browser_log": str(AUDIT_DIR / "synthetic-playwright.log"),
        }
        write_json(AUDIT_DIR / "synthetic-run-result.json", summary)
        return result.returncode
    finally:
        for process in (frontend, backend):
            if process and process.poll() is None:
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        backend_log.close()
        frontend_log.close()
        test_log.close()
        if RESOURCES_CREATED:
            await cleanup(DB_NAME, ROLE_NAME)


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f"Synthetic browser fixture stopped safely: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
