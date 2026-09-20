#!/usr/bin/env bash
# Test entrypoint that refuses to report a green the suite did not earn.
#
# tests/integration/conftest.py skips every database-backed test when
# CAREGIST_TEST_DATABASE_URL is unset. That skip is correct in itself, but it is
# invisible in an exit code: a run with no database reports "1061 passed" and
# exit 0 while every integration test, every RLS invariant and every finalize
# guard silently did not execute. A verification run recorded that way is a
# narrow claim presented as a broad one.
#
# `hermes verify` cannot prevent this on its own -- its recipe schema has no env
# field and its runner passes no env= to the subprocess, so it can only inherit
# the shell it was launched from. So the refusal lives here, in the repo, on the
# command the manifest and CI both invoke.
#
# Usage:
#   CAREGIST_TEST_DATABASE_URL=postgresql://... scripts/run_tests.sh [pytest args]
#   CAREGIST_ALLOW_UNIT_ONLY=1 scripts/run_tests.sh [pytest args]   # deliberate
set -euo pipefail

if [ -z "${CAREGIST_TEST_DATABASE_URL:-}" ]; then
  if [ "${CAREGIST_ALLOW_UNIT_ONLY:-}" = "1" ]; then
    cat >&2 <<'WARN'
================================================================================
UNIT-ONLY RUN -- NOT A FULL VERIFICATION
CAREGIST_TEST_DATABASE_URL is unset, so every database-backed test will SKIP:
the integration suite, the RLS invariants and the finalize guard did not run.
A pass from this run covers the unit level only. Do not record it as a green
full-suite verification.
================================================================================
WARN
  else
    cat >&2 <<'ERR'
ERROR: CAREGIST_TEST_DATABASE_URL is not set.

Without it every database-backed test skips and the suite exits 0 -- a green
that covers the unit level only. Refusing to run rather than produce that.

Run the full suite:
  CAREGIST_TEST_DATABASE_URL='postgresql://<role>@127.0.0.1:<port>/<db>' \
    scripts/run_tests.sh

The URL must target localhost/127.0.0.1/::1 and must not name a production
database; tests/integration/conftest.py enforces both. If the configured role is
a superuser or BYPASSRLS, the fixture provisions a dedicated NOSUPERUSER
NOBYPASSRLS role so the RLS assertions measure the invariant, not the bypass.

To run the unit level only, on purpose and on the record:
  CAREGIST_ALLOW_UNIT_ONLY=1 scripts/run_tests.sh
ERR
    exit 2
  fi
fi

exec pytest "$@"
