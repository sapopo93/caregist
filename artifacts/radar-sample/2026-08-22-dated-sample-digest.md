# CareGist Radar: dated sample digest (format sample)

**STATUS: INTERNAL FORMAT SAMPLE — not yet approved for sending.**
**This is a sample of the FORMAT, built from a DATED public-register mirror. It is NOT current CQC data and is NOT a promise that weekly digests will contain fresh data until the live CQC data path is verified.**

---

## What a weekly CareGist Radar digest looks like

**Territory:** Gloucestershire
**Snapshot as of:** 20/02/2026 (source mirror retrieved 24/02/2026)
**Window:** 14/02/2026 to 20/02/2026
**Selection rule:** deterministic — local authority with the highest count of supported events in the latest seven-day window ending on the newest source date in the snapshot; ties broken alphabetically by territory name.

### New registrations (5)

- **Rodley House** (1-26563133382)
  - Provider: Agincare (Somerset) Limited (1-18986016007)
  - Event: new registration — effective 18/02/2026
  - New value: registrationStatus=Registered; registrationDate=2026-02-18
  - Provenance: derived from location.registrationDate in the mirrored public CQC snapshot (no live API call)
  - Source: https://api.service.cqc.org.uk/public/v1/locations/1-26563133382

- **Grevill House** (1-26563133403)
  - Provider: Agincare (Somerset) Limited (1-18986016007)
  - Event: new registration — effective 18/02/2026
  - New value: registrationStatus=Registered; registrationDate=2026-02-18
  - Source: https://api.service.cqc.org.uk/public/v1/locations/1-26563133403

- **Paternoster House** (1-26563133431)
  - Provider: Agincare (Somerset) Limited (1-18986016007)
  - Event: new registration — effective 18/02/2026
  - Source: https://api.service.cqc.org.uk/public/v1/locations/1-26563133431

- **Henlow Court** (1-26563612989)
  - Provider: Agincare (Somerset) Limited (1-18986016007)
  - Event: new registration — effective 18/02/2026
  - Source: https://api.service.cqc.org.uk/public/v1/locations/1-26563612989

- **The Coombs** (1-26563613346)
  - Provider: Agincare (Somerset) Limited (1-18986016007)
  - Event: new registration — effective 18/02/2026
  - Source: https://api.service.cqc.org.uk/public/v1/locations/1-26563613346

### Rating changes

0 supported rating-change events in this window.

---

## Truthful framing for a buyer (candidate wording — needs Henry approval, D2)

"This is a dated sample of the CareGist Radar format, compiled from the public CQC register snapshot of 20 February 2026. Your weekly digests will cover the territory you choose. Each digest states the register snapshot date it was compiled from; if the official CQC data path is unavailable for a given week, we tell you before any payment and no digest is issued."

---

## Provenance block (inspectable artifacts)

- **Data source:** official public CQC register mirrored locally as NDJSON
  - `_locations_detail.ndjson` — 118,634 rows, 769,877,406 bytes, modified 24/02/2026 07:59:55
  - `_providers_detail.ndjson` — 63,144 rows, 97,596,653 bytes, modified 24/02/2026 06:36:06
- **Checksums (sha256):**
  - locations: `162dac50a6e63aec14bf90187df6f7fbe7b7ddef702b4bb8b4ff4d58284f58b8`
  - providers: `980f94e274e7cfa2682b769d5fbe8325d19a78f4e7e04c99db6d2cacec7133f0`
- **Latest source date in snapshot:** 20/02/2026
- **Generator:** `tools/generate_radar_territory_sample.py` (deterministic; `generated_at` anchored to snapshot date, not wall clock)
- **Regeneration proof:** running the generator on 22/08/2026 reproduced the existing sample byte-for-byte — sha256 `062c3b55ff815ac70cc81d06fc511669104629eb39afb4685a1eadeadc4f04ad` (md) and `b87e105c5fe29a129326e558d389f85acda81d7cc963ce55f713377200724cba` (json), unchanged before and after.
- **Fresh-data status (as of 22/08/2026):** official CQC monthly CSV URLs returned HTTP 403 (documented 13/08/2026 run); direct checks today returned HTTP 404 (care-directory URLs) and HTTP 502 (public API). **No verified live CQC data path exists yet.** Resolution is @operations' lane (escalated 23/08/2026).

---

## What this sample does and does not do

- DOES show the exact format, event types, provenance style, and truthfulness controls of a weekly digest.
- DOES NOT promise current data, completeness, or a specific territory — those depend on Henry's D1 (region) and D2 (sample-promise) decisions and a verified live data path.
- MUST NOT be sent to any buyer until Henry approves the wording and the outreach gate is open.
