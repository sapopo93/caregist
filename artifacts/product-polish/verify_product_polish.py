#!/usr/bin/env python3
"""Read-only checks for the local product-polish deliverables."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
    def handle_starttag(self, tag, attrs):
        if tag == "a" and dict(attrs).get("href"):
            self.items.append(dict(attrs)["href"])

def check_links(page):
    parser = Links()
    parser.feed(page.read_text())
    missing = [href for href in parser.items if not href.startswith(("http", "mailto:", "#")) and not (page.parent / href).resolve().exists()]
    assert not missing, (page, missing)
    return len(parser.items)

catalogue = json.loads((ROOT / "catalogue-evidence.json").read_text())
catalogue_html = ROOT / "catalogue/index.html"
catalogue_text = catalogue_html.read_text()
assert catalogue_text.count('class="card"') == len(catalogue["products"]) == 10
assert "No report exists to deliver today" in catalogue_text
assert "fresh weekly source path and four-week delivery are not verified" in catalogue_text

preview = ROOT / "brief-preview"
manifest = json.loads((preview / "delivery-manifest.json").read_text())
assert len(manifest["assets"]) == 4
for asset in manifest["assets"]:
    path = preview / asset["file"]
    assert path.exists() and path.stat().st_size == asset["bytes"]
    assert digest(path) == asset["sha256"]
assert len(PdfReader(preview / "caregist-birmingham-solihull-executive-brief.pdf").pages) == 4
preview_html = (preview / "index.html").read_text()
assert "Not retained in the pack" not in preview_html
assert "Three absence states" not in preview_html

radar = ROOT / "radar-pilot-sample/caregist-radar-gloucestershire-dated-format-sample.pdf"
radar_reader = PdfReader(radar)
assert len(radar_reader.pages) == 1
assert "Fresh weekly source and four-week delivery are not verified" in " ".join(radar_reader.pages[0].extract_text().split())

pages = [catalogue_html, preview / "index.html", ROOT / "radar-pilot-sample/index.html"]
report = {"result": "PASS", "catalogue_products": 10, "preview_assets": 4, "brief_pdf_pages": 4, "radar_sample_pdf_pages": 1, "checked_links": sum(check_links(page) for page in pages)}
(ROOT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
