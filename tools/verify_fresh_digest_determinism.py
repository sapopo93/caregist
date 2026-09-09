"""Determinism proof: regenerate the Gloucestershire digest from the verified
ODS edition into a temp dir and byte-compare against the staged product.
Read-only with respect to the staged artifacts. 2026-09-02."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from generate_radar_fresh_ods_digest import main as gen_main  # noqa: E402

ODS = ROOT / "artifacts" / "radar-live" / "2026-08-04_HSCA_Active_Locations.ods"
STAGED_MD = ROOT / "artifacts" / "radar-live" / "2026-08-04-fresh-weekly-digest-gloucestershire.md"
STAGED_JSON = ROOT / "artifacts" / "radar-live" / "2026-08-04-fresh-weekly-digest-gloucestershire.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if not ODS.exists() or not STAGED_MD.exists() or not STAGED_JSON.exists():
        print("missing inputs")
        return 1

    with tempfile.TemporaryDirectory(prefix="cg-det-") as tmp:
        tmp_md = Path(tmp) / "regenerated.md"
        tmp_json = Path(tmp) / "regenerated.json"
        sys.argv = ["generate_radar_fresh_ods_digest.py", str(ODS), "Gloucestershire", str(tmp_md), str(tmp_json)]
        rc = gen_main()
        if rc != 0:
            print(f"generator rc={rc}")
            return rc

        for label, staged, regen in [
            ("markdown", STAGED_MD, tmp_md),
            ("json", STAGED_JSON, tmp_json),
        ]:
            same = staged.read_bytes() == regen.read_bytes()
            print(f"{label}: byte-identical={same}")
            print(f"  staged   sha256 {sha256(staged)}")
            print(f"  regen    sha256 {sha256(regen)}")
            if not same:
                return 1
    print("DETERMINISM: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
