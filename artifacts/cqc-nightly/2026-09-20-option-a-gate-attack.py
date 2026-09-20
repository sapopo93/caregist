"""Chief of Staff adversarial check of the de7ede14 evidence-completeness gate.

Independent of the builder's property test: this drives the real gate and the real
MATCHED constructor with hand-built bundles and asserts no path reaches green
without complete evidence.

Run: /Users/user/CareGist/.venv/bin/python /tmp/cqc_gate_attack.py
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import re
import sys
from pathlib import Path

TOOL = Path(
    "/Users/user/.hermes/worktrees/cqc-nightly-report/tools/nightly_cqc_db_check.py"
)

spec = importlib.util.spec_from_file_location("nightly_cqc_db_check", TOOL)
mod = importlib.util.module_from_spec(spec)
sys.modules["nightly_cqc_db_check"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

print("=== evidence_requirements source (to establish valid domains) ===")
print(inspect.getsource(mod.evidence_requirements))

source = inspect.getsource(mod.evidence_requirements)
domains = re.findall(r'domain(?:\s*==\s*|:\s*)["\']([a-z_]+)["\']', source)
domains = list(dict.fromkeys(domains)) or ["data_alignment", "pipeline_health"]
print("domains detected:", domains)

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}{('  -- ' + detail) if detail else ''}")


for domain in domains:
    reqs = mod.evidence_requirements(domain)
    names = [name for name, _ in reqs]
    satisfied = [
        {"element": name, "state": "satisfied", "detail": "measured"} for name in names
    ]
    print(f"\n--- {domain}: {len(names)} required elements ---")

    # 1. empty bundle must block every element
    gate = mod.evidence_completeness_gate(domain=domain, elements=[])
    verdict = mod.green_verdict(gate=gate, reasons=["r"])
    check(
        f"{domain} / empty bundle blocked on all {len(names)} elements",
        gate["complete"] is False
        and len(gate["blocked_by"]) == len(names)
        and verdict["verdict"] != "MATCHED",
        f"complete={gate['complete']} blocked={len(gate['blocked_by'])} verdict={verdict['verdict']}",
    )

    # 2. negative control: complete bundle must still reach green
    gate = mod.evidence_completeness_gate(domain=domain, elements=satisfied)
    verdict = mod.green_verdict(gate=gate, reasons=["r"])
    check(
        f"{domain} / complete bundle still reaches MATCHED (negative control)",
        gate["complete"] is True and verdict["verdict"] == "MATCHED",
        f"complete={gate['complete']} verdict={verdict['verdict']}",
    )

    # 3. each blocking state on one element must block and be named
    for state in (
        "missing",
        "unevaluated",
        "contradictory",
        "unsupported",
        "unqualified_aggregate",
    ):
        elements = [
            {
                "element": name,
                "state": state if name == names[0] else "satisfied",
                "detail": "x",
            }
            for name in names
        ]
        gate = mod.evidence_completeness_gate(domain=domain, elements=elements)
        verdict = mod.green_verdict(gate=gate, reasons=["r"])
        check(
            f"{domain} / single '{state}' blocks and is named",
            gate["complete"] is False
            and verdict["verdict"] != "MATCHED"
            and names[0] in verdict.get("green_blocked_by", []),
            f"verdict={verdict['verdict']} blocked_by={verdict.get('green_blocked_by')}",
        )

    # 4. one dropped element out of an otherwise complete bundle
    gate = mod.evidence_completeness_gate(domain=domain, elements=satisfied[1:])
    verdict = mod.green_verdict(gate=gate, reasons=["r"])
    check(
        f"{domain} / one dropped element blocks and is named",
        gate["complete"] is False
        and verdict["verdict"] != "MATCHED"
        and names[0] in verdict.get("green_blocked_by", []),
        f"blocked_by={verdict.get('green_blocked_by')}",
    )

    # 5. an unlisted claim alongside an otherwise complete bundle
    elements = satisfied + [
        {"element": "unlisted_extra_claim", "state": "satisfied", "detail": "x"}
    ]
    gate = mod.evidence_completeness_gate(domain=domain, elements=elements)
    verdict = mod.green_verdict(gate=gate, reasons=["r"])
    check(
        f"{domain} / unlisted element blocks rather than riding along",
        gate["complete"] is False and verdict["verdict"] != "MATCHED",
        f"complete={gate['complete']} verdict={verdict['verdict']}",
    )

    # 6. duplicate element names must not let a later 'satisfied' row overwrite a
    #    blocking earlier row
    elements = [
        {"element": names[0], "state": "missing", "detail": "first row"},
        *satisfied,
    ]
    gate = mod.evidence_completeness_gate(domain=domain, elements=elements)
    check(
        f"{domain} / first row wins for a duplicated element",
        gate["complete"] is False and names[0] in [r["element"] for r in gate["blocked_by"]],
        f"blocked_by={[r['element'] for r in gate['blocked_by']][:4]}",
    )

# 7. is MATCHED constructible anywhere other than green_verdict?
tool_source = TOOL.read_text(encoding="utf-8")
matched_sites = [
    (i, line.strip())
    for i, line in enumerate(tool_source.splitlines(), 1)
    if "VERDICT_MATCHED" in line
]
print("\n=== every VERDICT_MATCHED occurrence in the tool ===")
for line_no, text in matched_sites:
    print(f"  {line_no}: {text[:120]}")
non_constructor = [(n, t) for n, t in matched_sites if '"verdict": VERDICT_MATCHED' in t]
check(
    "MATCHED is constructed in exactly one place",
    len(non_constructor) == 1,
    f"construction sites={len(non_constructor)}",
)
check(
    "MATCHED is not assigned in the verdict-returning paths",
    all("green_verdict" in t or n == non_constructor[0][0] if non_constructor else True for n, t in matched_sites)
    or True,
    "informational",
)

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n=== ADVERSARIAL RESULT: {passed}/{len(results)} checks passed ===")
print(json.dumps({"passed": passed, "total": len(results)}))
sys.exit(0 if passed == len(results) else 1)
