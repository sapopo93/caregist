# Known failing tests — pre-existing, not caused by the CQC work (2026-09-20)

Two integration tests fail in this repository. They were checked to be **pre-existing** so that they are
not mistaken later for regressions from the CQC corrective commits, and so that they are not silently
absorbed into a green-sounding summary.

## The failures

```
tests/integration/test_crm_security_invariants.py::test_migration_055_rolls_back_reapplies_and_forces_worker_rls
tests/integration/test_crm_security_invariants.py::test_forced_rls_worker_visibility_tenant_fk_and_agent_lock
```

Command (test database, no production access):

```
CAREGIST_TEST_DATABASE_URL='postgresql://cqctest@127.0.0.1:5599/cqc_test_admin' PYTHONPATH=. \
  /Users/user/CareGist/.venv/bin/python -m pytest tests/integration/test_crm_security_invariants.py -q
```

## Evidence that they are pre-existing

| Check | Result |
|---|---|
| Same file at the parent commit `1ac082d` (separate worktree, same env) | **2 failed, 7 passed** |
| Same file at the CEQ corrective `3456195` | 2 failed, 7 passed |
| Last commit to touch that test file | `044d12d` "Rehearse legacy rollback against its dependency boundary" — unrelated to CQC |
| Does `3456195` touch that file? | **no** (0 path matches in the commit) |
| Do the CQC migrations 061/062/063 contain role/policy/RLS/grant/revoke? | **no matches** |

Because the failure reproduces at the commit *before* the CQC corrections, it cannot be attributed to
them.

## Claimed cause (not independently reproduced here)

The corrective builder reported that the local test cluster's connecting role is a superuser
(`cqctest | rolsuper = t | rolbypassrls = t`), so row-level security is bypassed and the tests'
non-superuser assertions cannot hold; demoting the role instead broke schema creation with
`asyncpg.exceptions.InsufficientPrivilegeError: permission denied for language c`. That described
diagnosis is plausible and consistent with the structural evidence above, but this artifact does NOT
claim to have reproduced it: the original error text seen on `1ac082d` was the assertion failure, not
the privilege error.

## Disposition

* Status: **pre-existing defect in the test environment**, outside the CQC nightly brief.
* Not fixed here, and not repaired by weakening anything.
* CORRECTION (added after the second independent review of the ratings workstream): the claim in the
  original version of this section — that a fully green `pytest tests` is not achievable locally — was
  **wrong**. The reviewer created a temporary non-superuser, non-bypass role, used the fixture's separate
  admin URL, and the full nine-test file then reported **9 passed in 1.85s**; a second standalone
  non-superuser schema probe also passed. The claimed `permission denied for language c` failure was not
  reproduced in this environment.
* Owner/next action (for the operator): connect the harness's schema-build path with the admin role and
  its RLS assertions with a non-superuser role. That is the whole fix; no code change is implied by these
  two failures.
* The relevant CQC suite is green: `222 passed in 7.91s` at `3456195` (independently re-run).
