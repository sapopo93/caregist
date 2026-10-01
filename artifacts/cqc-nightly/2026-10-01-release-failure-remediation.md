# Release failure remediation — 2026-10-01

Scope: PR #75 frontend audit failure and preview database authentication.
This is an implementation/evidence record, not independent product gate approval.

## Dependency fix

CI run 36848120329 failed its frontend npm audit step while type-checking,
180 unit tests, build and HTTP/degraded-mode checks passed. Compatible lockfile
updates resolve the reported advisories: Next.js 16.3.5 → 16.3.8, undici
6.28.0 → 6.29.0, brace-expansion 5.0.11 → 5.0.12, fast-uri 3.1.7 → 3.1.8.
The manifest now requires Next.js ^16.3.8. Local npm audit reports zero
vulnerabilities; all 180 unit tests and TypeScript validation passed.
Exact-commit CI and deployed verification remain required.

## Preview database fix

Deployment dpl_D1JURiUHZjRLVt5TcEWYExsEbvU9 correctly served 419856d on both
services but directory health reported auth_failed and databaseAvailable=false.
The release branch inherited a generic preview DATABASE_URL created 187 days
before this check. Existing remediation branches had their own overrides.

The existing development-scoped STAGING_DATABASE_URL was retrieved only into
process memory. Its direct Neon URL was rejected by @vercel/postgres createPool
with invalid_connection_string. The corresponding -pooler hostname authenticated
successfully with SELECT 1; no database writes were performed.

Encrypted DATABASE_URL and POSTGRES_URL overrides were then applied only to
Preview branch feat/primary-cta-check-your-territory. Production credentials,
other branches and product gate settings were not modified. A fresh deployment
must verify database mode and release identity before production promotion.

No secret values or provider connection strings are included in this record.
