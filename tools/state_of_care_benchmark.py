#!/usr/bin/env python3
"""Reproduce CQC State of Care 2025/26 register counts from CareGist data.

Read-only. Compares, for non-dormant registered services:

* care homes, homecare and supported-living totals;
* care homes by registered-places band (1-10, 11-49, 50+) and the share of
  homes and of beds in 50+ homes;
* registrations and registration endings in the 12 months to the export date.

Columns of the output:

``cqc_reference``     the published State of Care figure (as supplied in the
                      report-readiness brief; not re-checked here)
``cqc_register_apr``  CQC's own HSCA Active Locations file as at 1 Apr 2026,
                      dual registrations reduced to CQC's Primary ID
``caregist_apr``      CareGist's CQC export reconstructed as at 1 Apr 2026
                      (registered by then and not deregistered by then;
                      dormancy is only known as at the export date)
``caregist_now``      CareGist's CQC export as at its retrieval date
``caregist_db_now``   CareGist's served directory (care_providers ACTIVE;
                      it stores no dormancy flag, so dormant rows are included)

    DATABASE_URL=... python3 -m tools.state_of_care_benchmark \\
        --export .tmp/cqc-export-20261020-final/_locations_detail.ndjson \\
        --hsca-ods cqc_active_locations_20260401.ods \\
        --out artifacts/report-readiness/2026-10-24/step1b
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterable

from tools.import_cqc_latest_ratings import iter_sheet_rows
from tools.report_sources import export_cutoff, iter_export, parse_day, readonly_connection, sha256_file

#: Published State of Care 2025/26 values supplied in the brief. ``None`` means
#: the brief gives no figure for that measure.
CQC_REFERENCE = {
    "homecare": 13_500,
    "supported_living_min": 4_500,
    "large_home_share_of_homes": 0.23,
    "large_home_share_of_beds": 0.70,
}
CQC_REFERENCE_NOTE = (
    "Reference values as supplied in .warroom/REPORT_READINESS_BRIEF.md: ~13,500 homecare "
    "(Apr 2026), >4,500 supported living, large homes 23% of care homes holding 70% of beds. "
    "Not independently re-checked against the State of Care publication in this run."
)
BANDS = ("1-10", "11-49", "50+", "unknown")


@dataclass(frozen=True)
class Service:
    location_id: str
    care_home: bool
    beds: int | None
    homecare: bool
    supported_living: bool
    dormant: bool


def band(beds: int | None) -> str:
    if not beds or beds <= 0:
        return "unknown"
    if beds <= 10:
        return "1-10"
    if beds <= 49:
        return "11-49"
    return "50+"


def measures(services: Iterable[Service]) -> dict:
    live = [s for s in services if not s.dormant]
    homes = [s for s in live if s.care_home]
    by_band = {b: 0 for b in BANDS}
    beds_by_band = {b: 0 for b in BANDS}
    for s in homes:
        b = band(s.beds)
        by_band[b] += 1
        beds_by_band[b] += s.beds or 0
    sized = sum(by_band[b] for b in ("1-10", "11-49", "50+"))
    total_beds = sum(beds_by_band.values())
    return {
        "care_homes": len(homes),
        "homecare": sum(s.homecare for s in live),
        "supported_living": sum(s.supported_living for s in live),
        "care_homes_by_band": by_band,
        "beds_by_band": beds_by_band,
        "care_home_beds": total_beds,
        "large_home_share_of_homes": round(by_band["50+"] / sized, 4) if sized else None,
        "large_home_share_of_beds": round(beds_by_band["50+"] / total_beds, 4) if total_beds else None,
    }


def _gac(row: dict) -> set[str]:
    return {str(g.get("description") or "") for g in row.get("gacServiceTypes") or [] if isinstance(g, dict)}


def _beds(value) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def service_from_export(row: dict) -> Service:
    gac = _gac(row)
    return Service(
        location_id=row.get("locationId") or "",
        care_home=row.get("careHome") == "Y",
        beds=_beds(row.get("numberOfBeds")),
        homecare="Domiciliary care service" in gac,
        supported_living="Supported living service" in gac,
        dormant=row.get("dormancy") == "Y",
    )


def registered_at(row: dict, as_at: date) -> bool:
    start = parse_day(row.get("registrationDate"))
    if not start or start > as_at:
        return False
    if row.get("registrationStatus") == "Registered":
        return True
    end = parse_day(row.get("deregistrationDate"))
    return bool(end and end > as_at)


def is_dual_secondary(dual_registered: str, primary_flag: str) -> bool:
    """CQC marks each dual-registered line 'Dual Registration' and flags the one
    to keep for provision counts with Primary ID = 'Y'; the other line is dropped."""
    return bool(dual_registered.strip()) and primary_flag.strip().upper() != "Y"


def load_hsca(path: Path) -> tuple[list[Service], dict]:
    rows = iter_sheet_rows(path, "HSCA_Active_Locations")
    header = next(rows)
    col = {n: i for i, n in enumerate(header)}
    out, dual_dropped = [], 0
    for r in rows:
        r = r + [""] * (len(header) - len(r))
        lid = r[col["Location ID"]]
        if is_dual_secondary(r[col["Location Dual Registered"]], r[col["Primary ID (Dual registration locations)"]]):
            dual_dropped += 1
            continue
        out.append(Service(
            location_id=lid,
            care_home=r[col["Care home?"]] == "Y",
            beds=_beds(r[col["Care homes beds"]]),
            homecare=r[col["Service type - Domiciliary care service"]] == "Y",
            supported_living=r[col["Service type - Supported living service"]] == "Y",
            dormant=r[col["Dormant (Y/N)"]] == "Y",
        ))
    return out, {"rows_kept": len(out), "dual_registration_lines_dropped": dual_dropped}


DB_SQL = """
SELECT id,
       COALESCE(service_types, '') ILIKE '%care home service%' AS care_home,
       number_of_beds,
       COALESCE(service_types, '') ILIKE '%Domiciliary care service%' AS homecare,
       COALESCE(service_types, '') ILIKE '%Supported living service%' AS supported_living
FROM care_providers
WHERE UPPER(status) = 'ACTIVE'
"""


def load_db() -> list[Service]:
    conn = readonly_connection()
    with conn.cursor() as cur:
        cur.execute(DB_SQL)
        return [Service(r[0], bool(r[1]), r[2], bool(r[3]), bool(r[4]), False) for r in cur.fetchall()]


#: Classifies one ended registration. Returns a class name; only
#: ``confirmed_closure`` counts as a closure in movement figures.
EndingClassifier = Callable[[dict], str]


def naive_classifier(row: dict) -> str:
    return "confirmed_closure"


def movement(rows: list[dict], *, window_end: date, classify: EndingClassifier) -> dict:
    start = window_end - timedelta(days=364)
    out = {}
    for label, pick in (
        ("care_homes", lambda r: r.get("careHome") == "Y"),
        ("homecare", lambda r: "Domiciliary care service" in _gac(r)),
    ):
        registrations = endings = closures = 0
        by_class: dict[str, int] = {}
        for r in rows:
            if not pick(r):
                continue
            reg = parse_day(r.get("registrationDate"))
            if reg and start <= reg <= window_end:
                registrations += 1
            end = parse_day(r.get("deregistrationDate"))
            if r.get("registrationStatus") == "Deregistered" and end and start <= end <= window_end:
                endings += 1
                kind = classify(r)
                by_class[kind] = by_class.get(kind, 0) + 1
                closures += kind == "confirmed_closure"
        out[label] = {
            "window": [start.isoformat(), window_end.isoformat()],
            "registrations": registrations,
            "registration_endings": endings,
            "confirmed_closures": closures,
            "endings_by_class": dict(sorted(by_class.items())),
        }
    return out


def _gap(value, reference):
    if value is None or reference is None:
        return None
    return round(value - reference, 4)


def comparison_table(columns: dict[str, dict]) -> list[dict]:
    refs = {
        "care_homes": None,
        "homecare": CQC_REFERENCE["homecare"],
        "supported_living": CQC_REFERENCE["supported_living_min"],
        "large_home_share_of_homes": CQC_REFERENCE["large_home_share_of_homes"],
        "large_home_share_of_beds": CQC_REFERENCE["large_home_share_of_beds"],
    }
    rows = []
    for metric, ref in refs.items():
        row = {"metric": metric, "cqc_reference": ref}
        for name, m in columns.items():
            row[name] = m[metric]
            row[f"{name}_gap_vs_reference"] = _gap(m[metric], ref)
        rows.append(row)
    for b in BANDS:
        row = {"metric": f"care_homes_{b}", "cqc_reference": None}
        for name, m in columns.items():
            row[name] = m["care_homes_by_band"][b]
        rows.append(row)
    return rows


def run(args, classify: EndingClassifier, closure_logic: str) -> dict:
    as_at = parse_day(args.as_at)
    export_rows = list(iter_export(args.export))
    window_end = export_cutoff(args.export, args.window_end, export_rows)
    now = [service_from_export(r) for r in export_rows if r.get("registrationStatus") == "Registered"]
    apr = [service_from_export(r) for r in export_rows if registered_at(r, as_at)]
    columns = {"caregist_now": measures(now), "caregist_apr": measures(apr)}
    sources = {
        "export": str(args.export),
        "export_sha256": sha256_file(args.export),
        "export_window_end": window_end.isoformat() if window_end else None,
        "as_at_reconstruction": as_at.isoformat(),
    }
    if args.hsca_ods:
        hsca, hsca_meta = load_hsca(args.hsca_ods)
        columns = {"cqc_register_apr": measures(hsca), **columns}
        sources.update({"hsca_ods": str(args.hsca_ods), "hsca_sha256": sha256_file(args.hsca_ods), **hsca_meta})
    if not args.no_db:
        columns["caregist_db_now"] = measures(load_db())
    return {
        "closure_logic": closure_logic,
        "reference_note": CQC_REFERENCE_NOTE,
        "sources": sources,
        "limitations": [
            "caregist_apr applies dormancy as at the export date; a service dormant in April "
            "but active by October (or the reverse) is misclassified.",
            "caregist_db_now cannot exclude dormant services: care_providers stores no dormancy flag.",
            "CareGist columns do not reduce dual registrations; only cqc_register_apr applies "
            "CQC's Primary ID rule.",
            "No earlier CareGist snapshot than the 20 Oct 2026 export is held, so April values are "
            "a reconstruction from registration/deregistration dates, not a stored snapshot.",
        ],
        "columns": columns,
        "comparison": comparison_table(columns),
        "movement_12_months": movement(export_rows, window_end=window_end, classify=classify),
    }


def write_markdown(result: dict, path: Path) -> None:
    cols = list(result["columns"].keys())
    lines = [
        "# State of Care benchmark",
        "",
        f"Closure logic: **{result['closure_logic']}**. {result['reference_note']}",
        "",
        "| Metric | CQC reference | " + " | ".join(cols) + " |",
        "|---|---:|" + "---:|" * len(cols),
    ]
    for row in result["comparison"]:
        cells = []
        for c in cols:
            v, gap = row[c], row.get(f"{c}_gap_vs_reference")
            cells.append(f"{v}" + (f" ({gap:+})" if gap is not None else ""))
        lines.append(f"| {row['metric']} | {row['cqc_reference'] if row['cqc_reference'] is not None else '-'} | "
                     + " | ".join(cells) + " |")
    lines += ["", "Gap in brackets = column value minus CQC reference.", "", "## Movement, 12 months to export", ""]
    for k, v in result["movement_12_months"].items():
        lines.append(f"- {k}: {v['registrations']} registrations, {v['registration_endings']} registration "
                     f"endings, {v['confirmed_closures']} confirmed closures ({v['window'][0]} to {v['window'][1]}); "
                     f"endings by class {v['endings_by_class']}")
    lines += ["", "## Limitations", ""] + [f"- {x}" for x in result["limitations"]]
    path.write_text("\n".join(lines) + "\n")


def main(argv=None, classify: EndingClassifier | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", type=Path, required=True)
    ap.add_argument("--hsca-ods", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--as-at", default="2026-04-01")
    ap.add_argument("--window-end", help="end of the 12-month movement window (default: the export's "
                    "retrieval date from RECEIPT.json)")
    ap.add_argument("--closure-logic", choices=("naive", "classified"), default="classified")
    ap.add_argument("--no-db", action="store_true")
    args = ap.parse_args(argv)
    if classify is None:
        if args.closure_logic == "classified":
            from api.services.registration_endings import classifier_for_export

            classify = classifier_for_export(iter_export(args.export))
        else:
            classify = naive_classifier
    args.out.mkdir(parents=True, exist_ok=True)
    result = run(args, classify, args.closure_logic)
    stem = f"state_of_care_{args.closure_logic}"
    (args.out / f"{stem}.json").write_text(json.dumps(result, indent=1, default=str))
    write_markdown(result, args.out / f"{stem}.md")
    print(json.dumps(result["comparison"][:5], default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
