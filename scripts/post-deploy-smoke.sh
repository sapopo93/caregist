#!/usr/bin/env bash
# Caregist — post-deploy smoke tests
# Usage: bash scripts/post-deploy-smoke.sh [BASE_URL]
# Default BASE_URL: https://caregist.co.uk
set -euo pipefail

BASE="${1:-https://caregist.co.uk}"
PASS=0
FAIL=0

_ok()   { echo "[PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "[FAIL] $1"; FAIL=$((FAIL + 1)); }
_info() { echo "       $1"; }

echo "========================================================"
echo " Caregist smoke tests"
echo " Target: $BASE"
echo " Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "========================================================"
echo ""

# 1. Homepage returns 200
echo "--- 1. Homepage 200 OK ---"
CODE=$(curl -fsS -o /dev/null -w "%{http_code}" "$BASE" || echo "000")
if [ "$CODE" = "200" ]; then
  _ok "Homepage returned HTTP $CODE"
else
  _fail "Homepage returned HTTP $CODE (expected 200)"
fi
echo ""

# 2. Readiness endpoint reports overall OK
echo "--- 2. Health readiness endpoint ---"
HEALTH=$(curl -fsS "$BASE/api/v1/health/readiness" 2>/dev/null || echo '{"overall":"ERROR"}')
OVERALL=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('overall','MISSING'))" 2>/dev/null || echo "PARSE_ERROR")
if [ "$OVERALL" = "ok" ] || [ "$OVERALL" = "OK" ]; then
  _ok "Health readiness: overall=$OVERALL"
else
  _fail "Health readiness: overall=$OVERALL (expected ok)"
  _info "Full response: $HEALTH"
fi
echo ""

# 3. Signup form has separate marketing consent checkbox (PR #16 Trill)
echo "--- 3. Marketing consent checkbox present (PR #16 Trill) ---"
SIGNUP_HTML=$(curl -fsS "$BASE/signup" 2>/dev/null || echo "")
if echo "$SIGNUP_HTML" | grep -q 'name="marketing_consent"'; then
  _ok "marketing_consent checkbox found in signup form"
else
  _fail "marketing_consent checkbox NOT found in signup form"
fi
echo ""

# 4. Privacy page references H-Kay Limited (PR #10 Vellum — may be deferred)
echo "--- 4. Privacy page H-Kay Limited reference (PR #10 Vellum) ---"
PRIVACY_HTML=$(curl -fsS "$BASE/privacy" 2>/dev/null || echo "")
if echo "$PRIVACY_HTML" | grep -q 'H-Kay Limited'; then
  _ok "H-Kay Limited found on privacy page"
else
  # Vellum is deferred to June 1 — warn but don't hard-fail
  echo "[WARN] H-Kay Limited NOT found on privacy page (PR #10 Vellum deferred to 1 June 2026 — expected if not yet merged)"
fi
echo ""

# 5. Cookie banner present (PR #8 Lattice)
echo "--- 5. Cookie banner present (PR #8 Lattice) ---"
HOME_HTML=$(curl -fsS "$BASE/" 2>/dev/null || echo "")
if echo "$HOME_HTML" | grep -qE 'caregist_consent_v1|CookieBanner|cookie-banner'; then
  _ok "Cookie banner marker found in homepage HTML"
else
  _fail "Cookie banner NOT found in homepage HTML"
fi
echo ""

# 6. No leaked secrets in homepage HTML
echo "--- 6. No leaked secrets in homepage HTML ---"
if echo "$HOME_HTML" | grep -qE 'sk_live_|sk_test_|sk-ant-|AKIA[0-9A-Z]{16}|ghp_[0-9a-zA-Z]{36}'; then
  _fail "CRITICAL: Potential secret pattern found in homepage HTML"
  echo "$HOME_HTML" | grep -oE '(sk_live_|sk_test_|sk-ant-|AKIA[0-9A-Z]{0,4}|ghp_)[^ \"]+' | head -3
else
  _ok "No leaked secret patterns in homepage HTML"
fi
echo ""

# 7. NEXT_PUBLIC_API_KEY not referenced in HTML (PR #6 Spindle)
echo "--- 7. NEXT_PUBLIC_API_KEY absent from HTML (PR #6 Spindle) ---"
if echo "$HOME_HTML" | grep -q 'NEXT_PUBLIC_API_KEY'; then
  _fail "NEXT_PUBLIC_API_KEY string found in page HTML — stale bundle?"
else
  _ok "NEXT_PUBLIC_API_KEY not present in HTML"
fi
echo ""

# 8. API health endpoint on EC2 (local — only works if run from EC2)
echo "--- 8. API local health (EC2 only — skip if running remotely) ---"
if curl -fsS --max-time 3 http://localhost:8000/api/v1/health > /dev/null 2>&1; then
  LOCAL_HEALTH=$(curl -fsS http://localhost:8000/api/v1/health 2>/dev/null)
  _ok "Local API health: $LOCAL_HEALTH"
else
  echo "[SKIP] Cannot reach localhost:8000 — run on EC2 for local check"
fi
echo ""

echo "========================================================"
echo " Results: $PASS passed, $FAIL failed"
echo "========================================================"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "One or more checks failed. Do NOT consider the deploy complete."
  echo "Review failures above, fix, redeploy, and re-run this script."
  exit 1
else
  echo ""
  echo "All checks passed. Deploy looks healthy."
  echo "Check Sentry (https://sentry.io) for any new errors in the last 30 minutes."
fi
