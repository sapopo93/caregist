#!/usr/bin/env python3
"""Ad-hoc verification for tools/nightly_cqc_db_check.py + its cron wrapper.

Not a project suite: this repo has no test target for a new standalone tool.
Exercises the real database (read-only) and the real wrapper.
"""
import ast
import copy
import importlib.util
import json
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "nightly_cqc_db_check.py"
WRAPPER = Path("/Users/user/.hermes/profiles/ai-company-governed/scripts/cqc_nightly_check.sh")
PY = str(REPO / ".venv" / "bin" / "python")
OUT = Path(tempfile.mkdtemp(prefix="hermes-verify-out-"))

checks = 0
fails: list[str] = []


def check(name, cond, detail=""):
    global checks
    checks += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond else f"  <- {detail}"))
    if not cond:
        fails.append(name)


print("1. static contract")
src = SCRIPT.read_text()
ast.parse(src)
check("parses as Python", True)
check("opens a read-only session", "set_session(readonly=True" in src)
check("no hardcoded user path in logic", "/Users/user" not in src)

print("\n2. import")
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location("nightly_cqc", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
check("module imports", True)

print("\n3. read-only is real, not just declared")
conn = mod.connect_readonly()
cur = conn.cursor()
mode = mod.scalar(cur, "SHOW transaction_read_only")
check("transaction_read_only == on", str(mode).lower() in ("on", "true"), repr(mode))

print("\n4. live gather + anomaly logic")
data = mod.gather(conn, 24)
conn.close()
check("gather returns data", bool(data))
check("active-set comparison present", "delta" in data.get("match", {}))
check(
    "delta is internally consistent",
    data["match"]["delta"] == data["providers_active"] - data["match"]["source_total"],
)
items = mod.anomalies(data, None)
check("anomalies returns a list", isinstance(items, list), type(items).__name__)
if data["match"]["delta"]:
    check("small delta stays silent (within tolerance)", not any("active-set mismatch" in i for i in items), str(items))
loud = copy.deepcopy(data)
loud["match"]["delta"] = -2000
check("material delta raises a finding", any("active-set mismatch" in i for i in mod.anomalies(loud, None)))
check("an unchanged material delta stays silent", not any("active-set mismatch" in i for i in mod.anomalies(loud, None, {"match_delta": -2000})))

clean = copy.deepcopy(data)
clean["match"]["delta"] = 0
clean["changes_total"] = 0
clean["watermark"]["counts_match"] = True
clean["ledger_newest_age_hours"] = 1.0
clean["polls_7d"] = {"completed": 336, "total": 336, "required": 336}
clean["rating_destination"]["all_time_no_destination"] = 0
clean["rating_destination"]["window_share"] = 0.0
clean["failures_in_window"] = []
clean["polls_24h"] = 48
residual = mod.anomalies(clean, None)
check("a clean state yields no findings (silent path)", residual == [], f"residual={residual}")

print("\n5. render contract")
report = mod.render(data, None, {})
for heading in (
    "## Does the database match CQC?",
    "## What changed",
    "## Freshness and pipeline health",
    "## Data quality gaps",
    "## Refresh churn",
):
    check(f"render has {heading[3:]!r}", heading in report)
check("render tolerates empty previous state", isinstance(report, str) and len(report) > 200)

print("\n6. exit codes and artifacts")
run = subprocess.run(
    [PY, str(SCRIPT), "--out-dir", str(OUT), "--force-report"],
    capture_output=True, text=True, timeout=240,
)
check("script exits 0", run.returncode == 0, run.stderr[-300:])
md = list(OUT.glob("*-report.md"))
js = list(OUT.glob("*-report.json"))
state = OUT / "state.json"
check("report .md written", bool(md))
check("report .json written", bool(js))
check("state.json written", state.exists())
if state.exists():
    check("state.json is 0600", oct(stat.S_IMODE(state.stat().st_mode)) == "0o600",
          oct(stat.S_IMODE(state.stat().st_mode)))
    json.loads(state.read_text())
    check("state.json is valid JSON", True)
if js:
    payload = json.loads(js[0].read_text())
    check("json has data + anomalies", "data" in payload and "anomalies" in payload)

bad = subprocess.run([PY, str(SCRIPT), "--no-such-flag"], capture_output=True, text=True)
check("unknown flag exits 2", bad.returncode == 2, str(bad.returncode))

print("\n7. scheduler wrapper resolves and runs")
check("wrapper is executable", bool(WRAPPER.stat().st_mode & 0o111))
wrapped = subprocess.run(
    ["bash", str(WRAPPER), "--out-dir", str(OUT), "--force-report"],
    capture_output=True, text=True, timeout=240,
)
check("wrapper exits 0", wrapped.returncode == 0, wrapped.stderr[-300:])
check("wrapper emits the report on stdout", "CareGist nightly CQC check" in wrapped.stdout)

print("\n8. lint")
ruff = shutil.which("ruff") or str(REPO / ".venv" / "bin" / "ruff")
if Path(ruff).exists():
    lint = subprocess.run([ruff, "check", str(SCRIPT), str(Path(__file__))], capture_output=True, text=True)
    check("ruff clean", lint.returncode == 0, lint.stdout[-300:])
else:
    print("  SKIP  ruff not found")

shutil.rmtree(OUT, ignore_errors=True)
print(f"\nAD-HOC VERIFICATION: {checks - len(fails)}/{checks} checks passed")
if fails:
    print("failed: " + "; ".join(fails))
    sys.exit(1)
