from pathlib import Path
import json,csv,re,ast
from datetime import date
from bs4 import BeautifulSoup
P=Path(__file__).parent
rows=json.loads((P/'results.json').read_text())
requests=json.loads((P/'requests.json').read_text())+json.loads((P/'identity-api-requests.json').read_text())
req={(r['id'],r['kind']):r for r in requests}
for r in rows:
 lid=r['id'];api=json.loads((P/'raw'/f'{lid}-api.json').read_text());overall=(api.get('currentRatings') or {}).get('overall') or {}
 r.update(cqc_url=f'https://www.cqc.org.uk/location/{lid}',live_api_rating=overall.get('rating'),live_api_report_date=overall.get('reportDate'),live_api_location_id=api.get('locationId'),live_api_registration_status=api.get('registrationStatus'),source_file_claimed_date='2026-10-01 (live label; not independently established)',source_file_metadata_modified_at='2026-10-02T15:11:34Z',observation_timestamps={k:req[lid,k]['observed_at'] for k in ['cqc','caregist','filtered','api','detail']},search_url=req[lid,'caregist']['url'],filtered_url=req[lid,'filtered']['url'])
 if lid=='1-19886383752':r.update(cqc_inherited_overall_rating='Outstanding',website_verdict='context discrepancy: inherited Outstanding, no current inspection')
 if lid=='1-16491295796':r['website_verdict']='context discrepancy: no current inspection, file Outstanding from 2018'
 if lid=='1-125730630':r['cause']='Newer website publication on 13 October 2026; file/API do not capture it.'
 elif r['stratum']=='conflict' and lid!='1-19886383752':r['cause']='Unconditional API precedence selects an older API publication over newer website/file evidence.'
 elif lid in ['1-19886383752','1-16491295796']:r['cause']='Current-provider and previous-provider rating semantics need reconciliation; do not select by rating value alone.'
 else:r['cause']='No numerical overall discrepancy observed; absence does not prove no historic or service-level rating exists.'
 # Freeze plain-text extracts as reviewer-friendly complements to the raw HTML.
 for k in ['cqc','caregist','filtered','detail']:
  s=BeautifulSoup((P/'raw'/f'{lid}-{k}.html').read_bytes(),'html.parser')
  for x in s(['script','style']):x.decompose()
  (P/'raw'/f'{lid}-{k}.txt').write_text(s.get_text(' ',strip=True))
(P/'results.json').write_text(json.dumps(rows,indent=2))
fields=['id','name','stratum','status','overall_rating','live_api_rating','live_api_report_date','file_overall_rating','file_overall_rating_date','file_rating_source','file_rating_source_sha256','source_file_claimed_date','source_file_metadata_modified_at','cqc_url','cqc_rating','cqc_publication_date','cqc_not_inspected','cqc_inherited','caregist_rating','caregist_source_label','filtered_found','filtered_rating','implementation_match','website_verdict','cause','search_url','filtered_url','observation_timestamps']
with (P/'audit.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
# Reproduce the deployed reader with actual API payloads and explicit file fields.
tree=ast.parse((P/'source/api/services/territory_brief.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_current_rating_evidence')
ns={'_parse_date':lambda x:date.fromisoformat(x) if x else None};exec(compile(ast.Module(body=[node],type_ignores=[]),'frozen-release-reader','exec'),ns)
proof=[]
for r in rows:
 api=json.loads((P/'raw'/f"{r['id']}-api.json").read_text());api.update(file_overall_rating=r['file_overall_rating'],file_overall_rating_date=r['file_overall_rating_date'])
 rating,pub=ns['_current_rating_evidence'](api);proof.append(dict(id=r['id'],file_rating=r['file_overall_rating'],reader_rating=rating,reader_date=str(pub) if pub else None))
(P/'brief-reader-reproduction.json').write_text(json.dumps(proof,indent=2))
assert len(rows)==len({r['id'] for r in rows})==30
assert all(r['implementation_match'] for r in rows)
assert all(r['id']==r['live_api_location_id'] for r in rows)
assert sum(bool(r['caregist_source_label']) for r in rows)==20
assert all(not r['reader_rating'] for r in proof[:20])
assert all((r['file_overall_rating'] is None and r['independent_file_lookup'] is None) or (r['file_overall_rating']==r['independent_file_lookup'][0] and date.fromisoformat(r['file_overall_rating_date']).strftime('%d/%m/%Y')==r['independent_file_lookup'][1]) for r in rows)
print('Assertions passed: distinct IDs, 30 rule matches, 30 live API identities, 20 source labels, 25 file values/dates, 20 omissions by deployed Brief reader')
