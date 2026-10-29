from pathlib import Path
from bs4 import BeautifulSoup
import json,re
P=Path(__file__).parent
sample=json.loads((P/'sample.json').read_text())
def soup_for(path):
 s=BeautifulSoup(path.read_bytes(),'html.parser')
 # Resolve React's server-streamed HTML fragments, without reading script text as displayed UI.
 for _ in range(5):
  changed=False
  for t in list(s.select('template[id^="P:"]')):
   frag=s.find(id='S:'+t['id'][2:])
   if frag:
    t.replace_with(*list(frag.contents));frag.decompose();changed=True
  if not changed:break
 for x in s(['script','style']): x.decompose()
 return s
out=[]
for r in sample['rows']:
 lid=r['id'];s=soup_for(P/'raw'/f'{lid}-cqc.html')
 val=s.select_one('.overall-rating__value--value')
 main=s.select_one('main') or s
 text=main.get_text(' ',strip=True); full=s.get_text(' ',strip=True)
 dates=re.findall(r'(?:Report published:|Published)\s*(\d{1,2} [A-Za-z]+ \d{4})',text)
 result=dict(r,cqc_rating=val.get_text(' ',strip=True) if val else None,cqc_publication_date=dates[0] if dates else None,cqc_not_inspected='We have not inspected this service yet' in full,cqc_inherited='Ratings inherited from last inspection with previous provider' in full,cqc_excerpt=text[:3500])
 for k in ['caregist','filtered']:
  s=soup_for(P/'raw'/f'{lid}-{k}.html')
  articles=[a for a in s.select('article') if any('/provider/'+str(r['slug'] or lid) in link.get('href','') for link in a.select('a[href]'))]
  result[k+'_found']=len(articles)==1
  result[k+'_card_text']=articles[0].get_text(' ',strip=True) if articles else None
  if articles:
   a=articles[0]; badge=a.select_one('div.rounded-full.border');result[k+'_rating']=badge.get_text(' ',strip=True) if badge else None
   result[k+'_source_label']=next((p.get_text(' ',strip=True) for p in a.select('p') if 'Rating per CQC' in p.get_text()),None)
 expected=r['overall_rating'] or r['file_overall_rating'] or 'Rating not published'
 result['expected_display']=expected
 result['implementation_match']=result.get('caregist_rating')==expected and result.get('filtered_rating')==expected
 if result['cqc_rating']:
  result['website_verdict']='match' if result['cqc_rating']==expected else 'discrepancy'
 elif r['stratum']=='unrated':result['website_verdict']='no overall rating visible'
 else:result['website_verdict']='discrepancy - current/inherited status'
 out.append(result)
(P/'results.json').write_text(json.dumps(out,indent=2))
for r in out:print(r['id'],r['stratum'],'API',r['overall_rating'],'file',r['file_overall_rating'],'web',r['cqc_rating'],'display',r.get('caregist_rating'),'filter',r['filtered_found'],'impl',r['implementation_match'])
