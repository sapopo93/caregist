#!/usr/bin/env python3
"""One-off read-only check of CQC location pages for the Clitheroe sample (12 Nov 2026).

Reads each public cqc.org.uk/location/<id> page once, about one request a
second, and prints what the page shows next to what the sample says. Writes
nothing. No /search pages are read (robots.txt).
"""
import re, time, urllib.request, json
EXPECTED = {"1-18589594217": ["The Croft Care Home", "Good", 28], "1-25368808165": ["Castlewood", "Not yet rated", 68], "1-122606708": ["Elms House", "Good", 6], "1-27897873724": ["Elms House", "Good", 6], "1-147345360": ["Castleford Home for Older People", "Good", 47], "1-29250138974": ["Clitheroe Care Home", "Requires improvement", 28], "1-6477957902": ["Clitheroe Care Home", "Requires improvement", 28], "1-141306889": ["Thistle Manor", "Good", 33], "1-2017040253": ["Beech Grove Care Home", "Good", 33], "1-114969802": ["Abbeyfield Care Home Clitheroe", "Good", 40], "1-203276918": ["Lowfield house Limited", "Good", 24], "1-29716664953": ["Middleshaw Hills Care Home", "Not yet rated", 66], "1-22160719656": ["Middleshaw Hills Care Home", "Not yet rated", 66], "1-112588978": ["High Brake House", "Good", 35], "1-13303408414": ["Meadowfold Hyndburn Ribble Valley Short Break", "Not yet rated", 8], "1-134621100": ["Merlewood House", "Good", 6], "1-239928777": ["Townfield and Coach House", "Good", 28], "1-15929596951": ["Mill Lodge Residential Care Home", "Good", 16], "1-1466315840": ["The Manor House", "Good", 51], "1-127849497": ["Meadow Lodge Residential Care Home", "Good", 14], "1-9597116593": ["The Springfield", "Good", 2], "1-404517984": ["Blackburn Road", "Good", 7], "1-147345564": ["Woodlands Home for Older People", "Good", 50], "1-136264545": ["Hilton Residential Home", "Good", 21], "1-13420883737": ["Hope House", "Good", 42], "1-24955783485": ["Mercer Moors", "Not yet rated", 36], "1-1736387577": ["Altham Care Home", "Good", 36], "1-147345580": ["Woodside Home for Older People", "Good", 46], "1-20632189493": ["Wytham Lodge", "Not yet rated", 34], "1-202481229": ["Hazeldene Care Home", "Good", 60]}
RATING_RE = re.compile(r'overall-rating__value--value">([^<]+)<')
UA = "CareGist-ratings-check/1.0 (+https://caregist.co.uk)"
KEEP = ['1-18589594217', '1-25368808165', '1-27897873724', '1-29250138974', '1-6477957902', '1-29716664953', '1-22160719656', '1-13303408414', '1-15929596951', '1-13420883737', '1-24955783485', '1-20632189493']
for lid, (name, rating, beds) in EXPECTED.items():
    if lid not in KEEP:
        continue
    url = f"https://www.cqc.org.uk/location/{lid}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        m = RATING_RE.search(html)
        t = re.search(r"<title>([^<]*)</title>", html)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        ctx = [text[max(0, x.start()-100):x.end()+160] for x in re.finditer(r"(?i)(overall rating|not yet rated|no ratings?|has not been rated|previous (?:provider|rating)|rating (?:from|published))", text)][:3]
        bed = re.findall(r"[^.]{0,60}\b(?:beds?|bed capacity)\b[^.]{0,60}", text, flags=re.I)[:2]
        pub = re.findall(r"(?:Published|Report published|Latest report)[^0-9]{0,20}(\d{1,2} \w+ \d{4})", text)[:2]
        regs = re.findall(r"Registered (?:on|since)[^0-9]{0,10}(\d{1,2} \w+ \d{4})", text)[:1]
        print(json.dumps({"id": lid, "sample": [name, rating, beds], "page_rating": m.group(1).strip() if m else "none", "title": t.group(1).strip() if t else "", "bed_text": bed, "published": pub, "registered": regs, "ctx": ctx, "status": "ok"}))
    except Exception as e:
        print(json.dumps({"id": lid, "sample": [name, rating, beds], "status": f"error {e}"}))
    time.sleep(1.1)
