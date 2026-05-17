#!/usr/bin/env bash
# Caregist — generate all rotating secrets
# Usage: bash scripts/generate-all-keys.sh > /tmp/caregist-secrets.env
# Store output in password manager. NEVER commit this file's output.
set -euo pipefail

echo "# Caregist secrets — generated $(date -u +%Y-%m-%dT%H:%M:%SZ) — DO NOT COMMIT"
echo ""

echo "# --- PR #5 Forge: webhook subscription HMAC encryption key ---"
echo "# AES-256-GCM / 32 random bytes, base64-encoded"
echo "WEBHOOK_SECRET_KEY=$(openssl rand -base64 32)"
echo ""

echo "# --- PR #9 Spool: session TTL (no generation needed — set in .env) ---"
echo "# SESSION_TTL_SECONDS=2592000   # 30 days — copy this line directly into .env"
echo ""

echo "# ================================================================"
echo "# The following are PLACEHOLDERS. Fill from existing infrastructure."
echo "# ================================================================"
echo ""

echo "# DATABASE_URL — Neon dashboard -> Connection string"
echo "# DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>?sslmode=require"
echo ""

echo "# RESEND_API_KEY — Resend dashboard -> API keys"
echo "# RESEND_API_KEY=re_..."
echo ""

echo "# SENTRY_DSN — Sentry project settings -> DSN"
echo "# SENTRY_DSN=https://...@sentry.io/..."
echo "# NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/..."
echo ""

echo "# STRIPE_SECRET_KEY — Stripe dashboard -> API keys"
echo "# Rotation pattern: create new restricted key, update .env, restart API,"
echo "# verify health, then revoke old key. See PR #1 (Cog) for the full runbook."
echo "# STRIPE_SECRET_KEY=sk_live_..."
echo ""

echo "# STRIPE_WEBHOOK_SECRET — Stripe dashboard -> Webhooks -> signing secret"
echo "# STRIPE_WEBHOOK_SECRET=whsec_..."
echo ""

echo "# API_KEY — internal backend key used by Next.js server -> FastAPI"
echo "# Rotate post-PR #6 (Spindle) merge via Stripe rotation runbook pattern."
echo "# Generate a new opaque key:"
echo "# API_KEY=$(openssl rand -hex 32)"
echo ""

echo "# CQC_API_KEY — https://anypoint.mulesoft.com/exchange/portals/care-quality-commission-5/"
echo "# CQC_API_KEY=your_api_key_here"
echo ""

echo "# ICO_REG_NUMBER — DEFERRED TO 1 JUNE 2026 (after £40 ICO fee filed)"
echo "# ICO_REG_NUMBER=ZA######"
