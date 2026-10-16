import json, sys, re, zlib
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, "/home/claude/caregist")
from api.services.territory_brief import *
from api.services.territory_brief_render import render_brief_pdf

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
def loc(i, pid, name, reg, rating=None, rdate=None, hist=None, beds=None):
    cr = {"overall": {"rating": rating, "reportDate": rdate}, "reportDate": rdate} if rating else {}
    return {"locationId": f"1-9999{i:05d}", "name": name, "providerId": pid, "localAuthority": "Demoshire",
            "region": "West Midlands (SYNTHETIC)", "registrationDate": reg, "registrationStatus": "Registered",
            "dormancy": "N", "numberOfBeds": beds, "postalCode": "ZZ1 1ZZ",
            "gacServiceTypes": [{"description": "Homecare agencies"}], "currentRatings": cr,
            "historicRatings": hist or []}
H = lambda r, d: {"overall": {"rating": r}, "reportDate": d}
L = [
 loc(1,"1-8888001","Demo Homecare North","2026-08-04"),
 loc(2,"1-8888002","Demo Homecare South","2026-08-19"),
 loc(3,"1-8888003","Demo Visits East","2026-09-02"),
 loc(4,"1-8888004","Demo Visits West","2026-09-14"),
 loc(5,"1-8888005","Demo Care at Home A","2025-01-10","Inadequate","2026-09-01",[H("Good","2024-03-01")]),
 loc(6,"1-8888006","Demo Care at Home B","2024-05-01","Requires improvement","2026-08-20",[H("Good","2023-06-01")]),
 loc(7,"1-8888007","Demo Support Services C","2023-02-01","Requires improvement","2026-07-25",[H("Requires improvement","2024-01-01")]),
 loc(8,"1-8888008","Demo Group Branch 1","2022-04-01","Requires improvement","2026-09-10",[H("Good","2023-02-01")]),
 loc(9,"1-8888008","Demo Group Branch 2","2022-06-01","Inadequate","2026-09-12",[H("Requires improvement","2023-05-01")]),
 loc(10,"1-8888008","Demo Group Branch 3","2022-07-01","Requires improvement","2026-08-30",[H("Good","2023-07-01")]),
 loc(11,"1-8888009","Demo Existing Client Homecare","2026-08-25"),
 loc(12,"1-8888010","Demo Rated Good Visits","2021-01-01","Good","2026-09-05",[H("Good","2023-01-01")]),
]
P = [{"providerId": f"1-88880{n:02d}", "name": nm} for n, nm in [
 (1,"Demo Homecare Ltd"),(2,"Demo Homecare South Ltd"),(3,"Demo Visits East Ltd"),(4,"Demo Visits West Ltd"),
 (5,"Demo Care at Home A Ltd"),(6,"Demo Care at Home B Ltd"),(7,"Demo Support Services Ltd"),
 (8,"Demo Group Holdings Ltd"),(9,"Demo Existing Client Ltd"),(10,"Demo Rated Good Ltd")]]
(OUT/"loc.ndjson").write_text("\n".join(map(json.dumps, L))+"\n"); (OUT/"prov.ndjson").write_text("\n".join(map(json.dumps, P))+"\n")
ctx = PurchaseContext(order_reference="SYNTHETIC-DEMO", generated_at=datetime(2026,10,16,tzinfo=timezone.utc), terms_version=None)
OBJ = "SYNTHETIC: fictional consultancy 'Example Governance Partners' supporting West Midlands domiciliary care providers"
b = generate_territory_opportunity_brief(
  {"kind":"region","name":"West Midlands (SYNTHETIC)","window_days":120,"shortlist_target":10,
   "buyer_objective":OBJ,"excluded_provider_ids":["1-8888009"]}, ctx,
  locations_source=OUT/"loc.ndjson", providers_source=OUT/"prov.ndjson")
(OUT/"SYNTHETIC-DEMO-brief.pdf").write_bytes(render_brief_pdf(b))
(OUT/"SYNTHETIC-DEMO-shortlist.csv").write_text(brief_to_csv(b))
for o in b.shortlist: print(o.rank if hasattr(o,"rank") else "", o.organisation_name, "|", o.reason[:100])
print(b.executive_summary.get("buyer_scope"))
