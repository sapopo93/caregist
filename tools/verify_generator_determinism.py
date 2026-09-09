"""Determinism re-run proof: hash existing artifacts, regenerate to a fresh dir, compare."""
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXISTING_MD = ROOT / "artifacts/radar-sample/weekly-territory-sample.md"
EXISTING_JSON = ROOT / "artifacts/radar-sample/weekly-territory-sample.json"
REFRESH_DIR = ROOT / "artifacts/radar-sample/regeneration-proof"
REFRESH_DIR.mkdir(parents=True, exist_ok=True)

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
print("timestamp_utc:", ts)

existing_hashes = {}
for name, p in (("md", EXISTING_MD), ("json", EXISTING_JSON)):
    if not p.exists():
        print("MISSING existing artifact:", p)
        sys.exit(2)
    existing_hashes[name] = sha256(p)
    print(f"existing {name}: {existing_hashes[name]}  size={p.stat().st_size}")

# Regenerate into a FRESH dir, never overwriting the originals
cmd = [
    sys.executable,
    str(ROOT / "tools/generate_radar_territory_sample.py"),
    "--output-dir",
    str(REFRESH_DIR),
]
r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
print("generator stdout:", r.stdout.strip())
print("generator exit:", r.returncode)
if r.returncode != 0:
    print("generator stderr:", r.stderr[-2000:])
    sys.exit(3)

new_md = REFRESH_DIR / "weekly-territory-sample.md"
new_json = REFRESH_DIR / "weekly-territory-sample.json"
new_hashes = {"md": sha256(new_md), "json": sha256(new_json)}
print(f"new md: {new_hashes['md']}  size={new_md.stat().st_size}")
print(f"new json: {new_hashes['json']}  size={new_json.stat().st_size}")

match = existing_hashes["md"] == new_hashes["md"] and existing_hashes["json"] == new_hashes["json"]
print("BYTE_IDENTICAL:", "YES" if match else "NO")

# Record proof line
proof = REFRESH_DIR / "regeneration-proof.txt"
with open(proof, "w", encoding="utf-8") as f:
    f.write(f"timestamp_utc: {ts}\n")
    f.write(f"python: {sys.version.split()[0]}\n")
    f.write(f"cwd: {ROOT}\n")
    f.write(f"command: {cmd}\n")
    f.write(f"existing_md_sha256: {existing_hashes['md']}\n")
    f.write(f"existing_json_sha256: {existing_hashes['json']}\n")
    f.write(f"new_md_sha256: {new_hashes['md']}\n")
    f.write(f"new_json_sha256: {new_hashes['json']}\n")
    f.write(f"byte_identical: {match}\n")
print("proof written:", proof)
