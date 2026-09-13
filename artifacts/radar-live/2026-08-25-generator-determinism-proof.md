# Generator Determinism Proof — CareGist Radar territory sample

**Status:** VERIFIED BYTE-IDENTICAL (re-run 2026-09-01).

**Purpose:** prove the territory sample generator (`tools/generate_radar_territory_sample.py`) is deterministic — regenerating the weekly-territory sample into a fresh directory produces byte-for-byte identical output to the shipped artifacts. This file is the evidence artifact cited by `2026-09-01-draft-invoice-final.md` §Evidence trail ("determinism re-run: `artifacts/radar-live/2026-08-25-generator-determinism-proof.md` (byte-identical)").

**File-name note:** the artifact name carries the 2026-08-25 date to match the invoice citation; the recorded run below is dated 2026-09-01 (the file was verified to be missing on disk and re-created this date — see fix return `outputs/2026-09-01-pilot-bundle-fix-return.md`).

---

## Run record (2026-09-01)

- **Tool:** `tools/verify_generator_determinism.py` (hash existing artifacts → regenerate to fresh dir → compare).
- **Generator:** `tools/generate_radar_territory_sample.py --output-dir artifacts/radar-sample/regeneration-proof`.
- **Run timestamp (UTC):** 2026-09-01T04:45:02+00:00 (≈05:45 BST).
- **Exit code:** 0. Proof record also written to `artifacts/radar-sample/regeneration-proof/regeneration-proof.txt` by the tool.

### Hashes (SHA-256)

| Artifact | Existing (shipped) | Regenerated (fresh dir) | Byte-identical |
|---|---|---|---|
| `weekly-territory-sample.md` (size 3665) | `062c3b55ff815ac70cc81d06fc511669104629eb39afb4685a1eadeadc4f04ad` | `062c3b55ff815ac70cc81d06fc511669104629eb39afb4685a1eadeadc4f04ad` | **YES** |
| `weekly-territory-sample.json` (size 8699) | `b87e105c5fe29a129326e558d389f85acda81d7cc963ce55f713377200724cba` | `b87e105c5fe29a129326e558d389f85acda81d7cc963ce55f713377200724cba` | **YES** |

**Result: BYTE_IDENTICAL — YES** (both files).

### Generator output (recorded from run)

- Selected territory: Gloucestershire
- Window: 14/02/2026 to 20/02/2026
- Supported events: 5

---

*Recorded by: CareGist pilot bundle fix producer (Hermes), 2026-09-01. Regeneration wrote only to `artifacts/radar-sample/regeneration-proof/`; shipped originals untouched.*
