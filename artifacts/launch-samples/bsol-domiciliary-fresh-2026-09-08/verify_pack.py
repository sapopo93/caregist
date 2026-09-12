"""Read-only integrity checks against saved sources and final delivery files."""
import csv, hashlib, json, zipfile
import xml.etree.ElementTree as E
from collections import Counter
from pathlib import Path
from pypdf import PdfReader

b = Path(__file__).resolve().parent
root = b.parents[2]
p = json.loads((b/'pack-data.json').read_text())
with (b/'source/converted/2026-09-01-active-locations-HSCA_Active_Locations.csv').open(encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
expected = {r['Location ID']:r for r in rows if r['Location Local Authority'] in ['Birmingham','Solihull'] and r['Service type - Domiciliary care service']=='Y' and r['Dormant (Y/N)']=='N'}
assert set(expected) == {r['location_id'] for r in p['dataset']}
for r in p['dataset']:
    s = expected[r['location_id']]
    assert (r['provider_id'],r['location_name'],r['rating_as_published']) == (s['Provider ID'],s['Location Name'],s['Location Latest Overall Rating'])
counts = Counter(r['provider_id'] for r in p['dataset'])
assert len(p['shortlist']) == len({r['provider_id'] for r in p['shortlist']}) == 25
for r in p['shortlist']:
    assert r['local_locations'] == counts[r['provider_id']]
for m in p['metadata']['source_manifest']:
    assert hashlib.sha256((b/'source'/m['file']).read_bytes()).hexdigest() == m['sha256']
for c in p['web_checks']:
    assert c['result']=='MATCH'
    assert hashlib.sha256((b/'source/location-pages'/(c['location_id']+'.html')).read_bytes()).hexdigest() == c['sha256']
out = root/'outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44'
for filename,key in [('territory-dataset.csv','dataset'),('shortlist-25.csv','shortlist')]:
    with (out/filename).open(encoding='utf-8-sig') as f:
        exported = list(csv.DictReader(f))
    assert exported == [{k:str(v) for k,v in row.items()} for row in p[key]]
x = out/'caregist-birmingham-solihull-territory-brief.xlsx'
ns = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(x) as z:
    sheets = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
    assert len(sheets)==3
    for name in sheets:
        xml = E.fromstring(z.read(name))
        assert not xml.findall('.//m:c[@t="e"]',ns), name
    xml = E.fromstring(z.read('xl/worksheets/sheet1.xml'))
    for cell,value in [('B6',297),('B7',56),('B8',353),('B9',25)]:
        assert float(xml.find('.//m:c[@r="'+cell+'"]//m:v',ns).text)==value
    for name,col,rows in [('sheet2.xml','J',p['shortlist']),('sheet3.xml','P',p['dataset'])]:
        xml = E.fromstring(z.read('xl/worksheets/'+name))
        for i,row in enumerate(rows,6):
            cell = xml.find('.//m:c[@r="'+col+str(i)+'"]',ns)
            assert row['cqc_url'] in cell.find('m:f',ns).text
            assert cell.attrib.get('t') != 'e'
            assert cell.find('m:v',ns).text == (row['location_id'] if col=='J' else row['cqc_url'])
pdf = root/'output/pdf/caregist-birmingham-solihull-executive-brief.pdf'
reader = PdfReader(pdf)
assert len(reader.pages)==4
assert all(len(page.extract_text())>500 for page in reader.pages)
report = {'result':'PASS','scope':'Local sample integrity, not independent commercial approval','locations':353,'distinct_providers':329,'shortlist':25,'source_hashes':2,'representative_page_hashes':25,'csv_fields':'all match pack-data.json','xlsx_sheets':3,'xlsx_error_cells':0,'xlsx_source_link_formulas':378,'pdf_pages':4}
(b/'qa/verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
