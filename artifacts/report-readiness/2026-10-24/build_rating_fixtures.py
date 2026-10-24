"""Freeze the 22 Oct 2026 rating-audit sample as resolver test fixtures.

Inputs (read-only): the audit packet's audit.csv/results.json, its checksum-
verified ratings.ods (for the Inherited Rating flag), and registration /
API-date columns read from care_providers in a READ ONLY transaction.

    DATABASE_URL=... python artifacts/report-readiness/2026-10-24/build_rating_fixtures.py \
        AUDIT_DIR tests/fixtures/rating_audit_2026_10_22.json
"""
import csv, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.import_cqc_latest_ratings import iter_sheet_rows  # noqa: E402
import psycopg2  # noqa: E402

audit_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = list(csv.DictReader(open(audit_dir / "audit.csv")))
results = {r["id"]: r for r in json.load(open(audit_dir / "results.json"))}
ids = [r["id"] for r in rows]

inherited = {}
it = iter_sheet_rows(audit_dir / "source" / "ratings.ods", "Locations")
h = next(it); c = {n: i for i, n in enumerate(h)}
for r in it:
    r = r + [""] * (len(h) - len(r))
    if r[0] in ids and r[c["Domain"]] == "Overall" and r[c["Service / Population Group"]] == "Overall":
        inherited[r[0]] = r[c["Inherited Rating (Y/N)"]]

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.set_session(readonly=True)
with conn.cursor() as cur:
    cur.execute("select id, registration_date, last_published_rating_date, overall_rating from care_providers where id = any(%s)", (ids,))
    db = {r[0]: r[1:] for r in cur.fetchall()}

def d(text):
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(text)

fixtures = []
for r in rows:
    reg, api_date, db_rating = db[r["id"]]
    res = results[r["id"]]
    fixtures.append({
        "id": r["id"], "name": r["name"], "stratum": r["stratum"],
        "registration_date": reg.isoformat() if reg else None,
        "api_value": r["overall_rating"] or None,
        "api_publication_date": api_date.isoformat() if (api_date and r["overall_rating"]) else None,
        "db_overall_rating_at_build": db_rating,
        "file_value": r["file_overall_rating"] or None,
        "file_publication_date": r["file_overall_rating_date"] or None,
        "file_inherited_flag": {"Y": True, "N": False}.get(inherited.get(r["id"])),
        "file_sha256": r["file_rating_source_sha256"] or None,
        "website_value": r["cqc_rating"] or None,
        "website_publication_date": d(r["cqc_publication_date"]),
        "website_inherited": res.get("cqc_inherited"),
        "website_not_inspected": res.get("cqc_not_inspected"),
        "website_observed_on": res["observation_timestamps"]["cqc"][:10],
        "website_verdict": r["website_verdict"],
    })
json.dump({
    "source": "artifacts/rating-audit/2026-10-22 (audit.csv, results.json, source/ratings.ods sha256 aba66fd8...)",
    "file_edition_date": "2026-10-02",
    "file_edition_note": "CQC data-page download label and ODS metadata date; the live '1 Oct' label and the data cutoff are not independently verified.",
    "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "fixtures": fixtures,
}, open(out, "w"), indent=1)
print(len(fixtures), "fixtures written")
