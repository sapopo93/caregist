# UNFINISHED — CareGist

**Refreshed:** 2026-09-11 00:30 BST. Everything here is **incomplete**. None of it is "nearly
done" in the sense of being externally provable.

---

## Provably incomplete

| Item | State | What is missing |
|---|---|---|
| Authoritative CQC reconciliation | Never completed | `reconciledAt: null`, `sourceRetrievedAt: null`, `countsReconciled: false`. Last attempt failed at 36.79 %. |
| CQC source currency | Overdue | Source `02_september_2026`, 216.2 h old vs 192 h SLA — 24.2 h late. |
| Freshness watchdog | Crash-failing | `ModuleNotFoundError: pydantic_settings` in ~17 s, every scheduled run. |
| Production smoke gate | Red since 2026-09-03 | Expected SHA `61513e9` is not on `main`. |
| Release identity | Unverified | Backend `9127923` (= main); frontend `1c98de7` (2026-09-03). 9 commits of skew. |
| Real-Postgres migration proof | **Never run** | `tests/test_territory_brief_pg_integration.py` unexecuted. |
| Migration 060 applied to production | Not applied | `main` max migration is 058. |
| Instant-delivery code on `main` | Not merged | Exists only on `feat/territory-self-serve-scope` (tip `9fcd697`). |
| Self-serve checkout | Not purchasable | `checkoutReady: false`. |
| Solicitor-approved immediate-supply terms | Not obtained | Draft only, dated 2026-09-09. |
| Stripe live objects for the £795 brief | Unconfirmed | Vercel var exists; no reader on `main`; live status unknown. |
| Blob token / Resend key for delivery | Unverified | Checkout path 503s if either is absent. |

## Known-risky, not yet disproven

- **Frontend/backend skew of 9 commits** (2026-09-03 frontend vs 2026-09-09 backend) — I have
  not proven whether any of those 9 commits change behaviour the live frontend depends on.
  The live pricing copy does match `main`, which is inconsistent with the reported frontend
  SHA; either the SHA is misreported or the deployment did not promote. **Unresolved.**
- **GitHub deployment record vs served code** — a Production deployment for `9127923`
  (2026-09-09T01:25Z) is recorded while the frontend reports `1c98de7`.
- **~~`vitals` of the 5 duplicate commits~~ — RESOLVED 2026-09-11 00:35.** Split result, and
  the split matters:
  - `api/services/provider_intelligence.py` — **byte-identical** (6,325 B, sha256
    `e609086332295d56…` both sides). Pure duplicate commit.
  - `db/migrations/058_crm_provider_intelligence.sql` — **byte-identical** (8,570 B, sha256
    `e4388608418c48de…` both sides). Pure duplicate commit.
  - `frontend/components/PricingCTA.tsx` — **DIVERGED** (branch 9,047 B vs main 8,387 B).
  - `frontend/lib/caregist-config.ts` — **DIVERGED** (branch 9,249 B vs main 6,583 B).

  So the branch is a **mixed** collision: identical content where a merge would produce a
  spurious conflict, and genuinely divergent implementations of the same feature where a merge
  would silently pick a winner. Neither is acceptable unattended. This strengthens — it does
  not weaken — the case for cherry-picking an explicit file set rather than merging.
  *Method note: an earlier check of these two paths returned the empty-string hash
  `e3b0c44298fc1c14…` because the paths were wrong. That result was inconclusive, not evidence;
  it was re-run against the correct paths before any claim was made.*

## Explicitly not attempted (and why)

- **No merge, no deploy, no live Stripe change, no live data mutation, no outbound customer
  message** — all require Henry's explicit approval and none was sought here.
- **No independent reviewer assigned to the extracted build** — there is no artifact yet.
  Producer must not review its own work, so R2 stays `PARKED` until N5 lands.
- **No revenue-critical public journey proof** — requires the offer to be purchasable. It is
  not. Cannot be faked by a passing unit test.

## Preservation state (verified)

Uncommitted work is preserved before any repository operation:

| Artifact | Location | Evidence |
|---|---|---|
| Full branch bundle | `company-os/_preservation/caregist-20260911/feat-territory-self-serve-scope.bundle` | 17,989,940 bytes · `git bundle verify` → "records a complete history" · sha256 `b3300dbe0aeeeae3…` |
| Untracked artifacts | `company-os/_preservation/caregist-20260911/untracked-artifacts.tar.gz` | 162 entries · sha256 `4ac944c903e9cdf1…` |
| Manifest | `company-os/_preservation/caregist-20260911/untracked-manifest.txt` | 162 paths |
| Durable git tag | `preserve/territory-self-serve-20260911` → `9fcd697` | local ref |

The 12-commit branch is **not** lost and **not** merged. It can be reconstructed from the
bundle on any machine without this repo's worktrees.
