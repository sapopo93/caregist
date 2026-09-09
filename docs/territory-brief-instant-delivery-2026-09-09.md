# Territory Opportunity Brief - Slice 2 (fully instant delivery)

Status: **NOT READY to enable.** Pack generation is built and tested. The paid
delivery path is implemented at the unit level but is not end-to-end verified,
and there is a hard consent/Terms blocker plus a founder gate on Stripe object
creation.

`TERRITORY_SELF_SERVE_CHECKOUT_ENABLED` **must stay OFF.**

---

## 1. What is implemented and tested in this branch

| Component | File | Test | State |
|---|---|---|---|
| Pack generator (`generate_territory_opportunity_brief`) | `api/services/territory_brief.py` | `tests/test_territory_brief.py` (26) | Implemented + tested |
| Scope validation (allow-list from live data, no default fallback) | same | same | Implemented + tested |
| Deterministic ranking + per-org reason + territory insights + next actions | same | same | Implemented + tested |
| Dependency-free PDF writer | `api/services/pdf_writer.py` | via render tests | Implemented + tested |
| Brief renderer (executive brief + Appendix A) | `api/services/territory_brief_render.py` | `test_territory_brief*.py` | Implemented + tested |
| CSV export | `api/services/territory_brief.py::brief_to_csv` | `test_territory_brief*.py` | Implemented + tested |
| CLI dry-run tool | `tools/generate_territory_opportunity_brief.py` | manual + integration | Implemented + tested |
| Real-data integration test (1,422-location CQC extract) | `tests/test_territory_brief_integration.py` (7) | — | Implemented + tested |
| Stripe-confirmed fulfilment handler (idempotent, retry-safe) | `api/services/territory_brief_fulfilment.py` | `tests/test_territory_brief_fulfilment.py` (17) | Implemented, unit-tested only |
| Vercel Blob upload helper | `api/services/blob_upload.py` | `tests/test_blob_upload.py` (8) | Implemented, unit-tested only |
| DB schema (orders / consents / download tokens) | `db/migrations/060_territory_brief_fulfilment.sql` | governance test | Implemented, **not applied to any DB** |
| Feature flag + fail-closed startup gate | `api/config.py` | full suite (740) | Implemented + tested |

Regression: `740 passed, 22 skipped`. The 4 pre-existing failures on the base
commit (`test_crm_ai_safety` local NER model unavailable; 3×
`test_stripe_release_verifier` env-dependent) are unrelated to this change.

---

## 2. Wiring status (updated 2026-09-09)

**2a (checkout route) and 2b (webhook branch + expired/refund handlers) are now
implemented** on `feat/territory-self-serve-scope`, behind the fail-closed
`territory_self_serve_checkout_enabled` flag:

* `api/routers/billing.py` - `TerritoryBriefCheckoutRequest`,
  `POST /api/v1/billing/territory-brief-checkout`, the
  `_handle_checkout_completed` routing branch, plus `territory_brief_orders`
  in the `checkout.session.expired` and `charge.refunded` handlers.
* `api/services/territory_brief_delivery.py` (new) - `terms_evidence()`,
  `fulfilment_settings()`, `fulfilment_deps()`, `generate_pack()`,
  `upload_pack()`, `scope_catalogue()`, `_record_failure()`.
* `tests/test_billing_territory_brief_checkout.py` (new) - 10 tests.

Full regression after wiring: **751 passed, 22 skipped**; the 3 pre-existing
`test_stripe_release_verifier` failures are unrelated (verified against the base
commit).

**Still a spec (blind edit would collide with in-flight human work):** 2c
(frontend `consumePaidDownload` generalisation - `frontend/lib/directory-db.ts`
is under active development) and 2d (checkout UI + consent page).

**Still open - hard pre-enable gate:** §5 (Postgres generation source).
`territory_brief_delivery.generate_pack()` / `scope_catalogue()` read the
~734 MB mirrored CQC NDJSON snapshot, which is not in the serverless bundle;
`_snapshot_paths()` raises a clear error when it is absent. Those functions are
the only seam that must change.

None of the paid path can be end-to-end verified here (no isolated Postgres, no
Stripe test webhook endpoint, no Blob token, no staging deploy).

### 2a. Checkout route - `api/routers/billing.py`  *(IMPLEMENTED)*

Implemented, modelled on `create_dataset_checkout` but with clean naming.
Original spec sketch retained below for reference:

```python
class TerritoryBriefCheckoutRequest(BaseModel):
    email: EmailStr
    scope_kind: Literal["local_authority", "region"]
    scope_name: str = Field(min_length=2, max_length=80)
    window_days: int = Field(90, ge=7, le=365)
    model_config = {"extra": "forbid"}

@router.post("/territory-brief-checkout", dependencies=[Depends(check_ip_rate_limit)])
async def create_territory_brief_checkout(req, request: Request) -> dict:
    if not settings.territory_self_serve_checkout_enabled:
        raise HTTPException(503, "Territory Opportunity Brief checkout is not available yet.")
    if not (settings.stripe_secret_key and settings.stripe_price_territory_brief
            and settings.blob_read_write_token and settings.resend_api_key):
        raise HTTPException(503, "Territory Opportunity Brief checkout is not configured.")
    cfg = _territory_brief_settings()           # reads territory_brief_terms_* + consent_sha
    # 1. validate scope against live source data BEFORE taking payment
    #    (known_territories(...) / validate_scope(...)) -> 422 on unknown territory
    # 2. INSERT territory_brief_orders(... status='pending', scope_*)
    # 3. stripe.checkout.Session.create(
    #        mode="payment",
    #        line_items=[{"price": settings.stripe_price_territory_brief, "quantity": 1}],
    #        consent_collection={"terms_of_service": "required"},
    #        custom_text={"terms_of_service_acceptance": {"message": TERRITORY_BRIEF_CONSENT_TEXT}},
    #        success_url=f"{app_url}/territory-opportunity-brief/success?session_id={{CHECKOUT_SESSION_ID}}",
    #        cancel_url=f"{app_url}/territory-opportunity-brief?cancelled=1",
    #        expires_at=+30min,
    #        invoice_creation={"enabled": True},
    #        metadata=build_checkout_metadata(order_id, scope, cfg),   # from territory_brief_fulfilment
    #        idempotency_key=f"caregist-territory-brief-{order_id}",
    #    )
    # 4. UPDATE territory_brief_orders SET stripe_checkout_session_id=... WHERE id=... AND status='pending'
    #    on Stripe error: UPDATE ... SET status='expired'
```

Client price/amount/status fields are rejected by `model_config extra="forbid"`;
the price is server-only. Scope is customer-controlled **text** but is validated
against the live LA/region list before any Stripe call and re-validated at
fulfilment, so it cannot select an arbitrary file or territory.

### 2b. Webhook routing - `api/routers/billing.py::_handle_checkout_completed`

One branch, next to the existing `full_dataset` branch (line 1586):

```python
if metadata.get("type") == territory_brief_fulfilment.METADATA_TYPE:
    await territory_brief_fulfilment.fulfil_territory_brief_order(
        conn, session, cfg=_territory_brief_settings(), deps=_territory_brief_deps(),
    )
    return
```

`_territory_brief_deps()` wires:
* `generate` -> load the CQC snapshot (DB-backed in production, not the ndjson),
  call `generate_territory_opportunity_brief`, `render_brief_pdf`, `brief_to_csv`,
  return `GeneratedPack`.
* `upload` -> `blob_upload.put_blob(f"territory-briefs/{order_id}/{secrets.token_hex(16)}/brief.{kind}", ...)`.
* `retrieve_session` -> `lambda sid: stripe.checkout.Session.retrieve(sid, expand=["line_items"])`.
* `record_failure` -> `async with get_connection() as c: UPDATE territory_brief_orders SET status='failed', last_error=$2 ...`
  (fresh connection so the note survives the webhook rollback).
* `write_audit_log` -> `api.utils.audit.write_audit_log`.

Also add `territory_brief_orders` to the `checkout.session.expired` and
`charge.refunded` handlers (mirror the `full_dataset_orders` updates at lines
1421-1428 and 1948-1957); on refund, also expire outstanding
`territory_brief_download_tokens`.

**Idempotency** is already guaranteed three ways: the shared
`stripe_processed_events` transactional insert (billing webhook, line 1395); the
`FOR UPDATE` order lock; and the explicit `status == 'fulfilled'` early return in
`fulfil_territory_brief_order`. `pending_emails` and
`territory_brief_download_tokens` inserts are `ON CONFLICT DO NOTHING`.

### 2c. Delivery - `frontend`

`frontend/app/api/export/route.ts` currently calls `consumePaidDatasetDownload`.
Generalise **additively** (do not rename the existing function - webhook replay
and refunds still use it):

* New `frontend/lib/paid-download.ts` exporting `consumePaidDownload(token)` that
  tries `dataset_download_tokens` -> `full_dataset_artifacts` (existing query)
  **and** `territory_brief_download_tokens` -> `territory_brief_orders`
  (`status='fulfilled'`, `download_count < max_downloads`, not expired),
  returning `{ blob_pathname, filename, content_type }`.
* `consumePaidDatasetDownload` becomes a thin wrapper over it.
* `route.ts`: gate on `DIRECTORY_EXPORT_DELIVERY_ENABLED || FULL_DATASET_CHECKOUT_ENABLED
  || TERRITORY_SELF_SERVE_CHECKOUT_ENABLED`; call `consumePaidDownload`; keep the
  existing `issueSignedToken` + `presignUrl({ access: "private", validUntil: +5min })`
  + 307 redirect. Set `Content-Disposition` from the returned filename.

The download identifier is `secrets.token_urlsafe(32)` hashed with SHA-256 at
rest (`territory_brief_download_tokens.token_hash`), 30-day expiry, 5 uses. The
Blob object is only reachable via a 5-minute presigned private URL. No public
Blob URL is ever emitted.

### 2d. Checkout UI + consent - `frontend`

The `/territory-opportunity-brief` page needs: territory picker (validated
against `/api/territory/coverage` or equivalent), visible scope + £795 + "what
you get", and an **explicit** pre-payment checkbox that must be ticked to enable
the pay button, carrying the exact approved immediate-supply wording. Stripe's
`consent_collection.terms_of_service: "required"` is a second, server-verified
gate (`consent.terms_of_service == "accepted"` is checked at fulfilment), so
checkout cannot complete without it even if the SPA is bypassed.

---

## 3. Consent / Terms blocker (the reason this is NOT READY regardless of code)

`FULL_DATASET_CONSENT_TEXT` (`api/routers/billing.py:38`) says the buyer loses
the right to cancel "once download access is provided" for "the digital
dataset". It was written for a **static, instantly-downloadable** dataset.

The **published Business Terms** for the Territory Opportunity Brief
(`frontend/app/terms/page.tsx`, v2.1, in force 9 Sep 2026, on
`codex/territory-offer-20260909` / `feat/territory-self-serve-scope`) describe a
**materially different product**:

> "CareGist confirms the scope and the relevant source path **before it sends a
> payment link or accepts payment**." … "The buyer may **cancel by email before
> work begins and receive a full refund**." … "the delivery target … is **three
> working days** after … the written scope confirmation".

This is a bespoke, human-mediated, cancellable, 3-working-day service. It is the
**opposite** of instant self-serve supply with loss of cancellation rights.

**You cannot reuse `FULL_DATASET_CONSENT_TEXT`, and you cannot enable instant
self-serve delivery against the currently published Terms.** Enabling Slice 2
requires:

1. A revised Business Terms section for the Brief that describes instant
   self-serve generation and an express immediate-supply / loss-of-cancellation
   consent (CCRs 2013 reg. 37 / reg. 28(1)(b) style), **reviewed and approved by
   the solicitor** who approved v2.0/v2.1.
2. The approved wording placed in `TERRITORY_BRIEF_CONSENT_TEXT`
   (`api/services/territory_brief_fulfilment.py`), its SHA-256 in
   `TERRITORY_BRIEF_CONSENT_SHA256`, and the Terms version + hash in
   `TERRITORY_BRIEF_TERMS_VERSION` / `TERRITORY_BRIEF_TERMS_SHA256`.
3. The config startup gate (already implemented) then permits the flag; until
   then it hard-fails `validate_production()`.

This is a genuine legal-interpretation question, not a coding task. It is a
launch blocker. **Do not invent the wording.**

---

## 4. Founder / operational gates (independent of the above)

* Commit `53511dc` on `feat/territory-self-serve-scope`:
  "Live Stripe objects and Payment Links require founder approval and **must not
  be created by an automated agent**." The £795 Stripe Product/Price
  (`STRIPE_PRICE_TERRITORY_BRIEF`) is `pending_creation` in
  `deploy/stripe-price-manifest.json`. A human must create it (test + live) with
  customer-facing naming that does **not** use "full dataset".
* No Stripe **test-mode webhook endpoint** exists (per
  `docs/radar-checkout-audit-2026-08-14.md` §D). Needed for any real E2E test.
* No isolated staging Postgres / protected preview wired to test Stripe + a Blob
  store. Migration 060 has never run.
* `BLOB_READ_WRITE_TOKEN` is not configured for the API runtime.

---

## 5. Production generation source

The generator currently reads the `_locations_detail` / `_providers_detail`
NDJSON snapshots (the same as `generate_radar_territory_sample.py`). Loading the
full 734 MB file takes ~70 s - unacceptable inside a webhook. Before enabling,
`_territory_brief_deps().generate` must be pointed at the **canonical Postgres
tables** (`care_providers` + rating history + `provider_state_events` /
`trusted_event_ledger`) or a pre-built per-edition territory index, so
generation is sub-second. The ranking/reason/render code does not change; only
the row source does. This is tracked as the main pre-enable engineering task.

---

## 6. Enable checklist (all required)

- [ ] Solicitor-approved immediate-supply consent wording + Terms section for the Brief
- [ ] `TERRITORY_BRIEF_TERMS_VERSION` / `_SHA256` / `_CONSENT_SHA256` set to approved values
- [ ] Founder-created £795 Stripe Product + Price (test + live), no "full dataset" naming
- [ ] `STRIPE_PRICE_TERRITORY_BRIEF`, `BLOB_READ_WRITE_TOKEN` configured
- [ ] Migration 060 applied to staging + production (isolated Postgres integration run first)
- [x] Checkout route (2a) + webhook branch / expired / refund (2b) implemented (flag OFF)
- [ ] Download generalisation (2c) + checkout UI & consent page (2d) implemented
- [ ] Generation source switched to Postgres (§5) — `territory_brief_delivery.generate_pack` / `scope_catalogue`
- [ ] Stripe test webhook endpoint on a protected preview; full E2E matrix recorded
      (valid pay, duplicate webhook, generation failure + retry, missing/unknown scope,
      wrong product, unauthorised download, refund)
- [ ] One real Stripe **test-mode** transaction end to end, brief opened and inspected
- [ ] `BILLING_CHECKOUT_ENABLED=true` and only then `TERRITORY_SELF_SERVE_CHECKOUT_ENABLED=true`
