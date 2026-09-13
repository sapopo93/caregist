"""Inspect CQC ODS structure without odfpy. Read-only; prints sheet names, header rows, and sample cells."""
import zipfile
import xml.etree.ElementTree as ET
import sys

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

path = sys.argv[1]
max_rows = int(sys.argv[2]) if len(sys.argv) > 2 else 3

with zipfile.ZipFile(path) as z:
    names = z.namelist()
    print("ZIP entries:", len(names))
    for n in names:
        if "content" in n or "styles" in n:
            print("  entry:", n)
    with z.open("content.xml") as f:
        tree = ET.parse(f)

root = tree.getroot()
body = root.find("office:body", NS)
spread = body.find("office:spreadsheet", NS)
tables = spread.findall("table:table", NS)
print("Sheets:", len(tables))
for t in tables:
    print("  sheet:", t.get("{%s}name" % NS["table"]))

# Data sheet: dump header + sample rows
sheet_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 1
t = tables[sheet_idx]
rows = t.findall("table:table-row", NS)
print("Rows in sheet 0:", len(rows))
for ri, r in enumerate(rows[: max_rows + 1]):
    cells = []
    for c in r.findall("table:table-cell", NS):
        rep = int(c.get("{%s}number-columns-repeated" % NS["table"], "1"))
        txt = "".join(p.text or "" for p in c.findall(".//text:p", NS))
        cells.append(txt)
        if rep > 1:
            cells.extend([""] * (rep - 1))
    print(f"R{ri}:", cells[:25])
