from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,urllib.request,urllib.parse,hashlib,time
P=Path(__file__).parent
rows=json.loads((P/'sample.json').read_text())['rows']
def fetch(item):
 lid,kind,url=item
 dest=P/'raw'/f'{lid}-{kind}.html'
 t=datetime.now(timezone.utc).isoformat()
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; CareGist evidence audit)'})
  with urllib.request.urlopen(req,timeout=45) as r: data=r.read();status=r.status; final=r.url
  dest.write_bytes(data)
  return dict(id=lid,kind=kind,url=url,final_url=final,status=status,observed_at=t,path=str(dest),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 except Exception as e: return dict(id=lid,kind=kind,url=url,observed_at=t,error=str(e))
items=[]
for r in rows:
 lid=r['id']; rating=r['overall_rating'] or r['file_overall_rating']
 items.append((lid,'cqc',f'https://www.cqc.org.uk/location/{lid}'))
 # postcode narrows results while verifying exact ID in returned cards
 query={'q':r['postcode'] or r['name']}
 items.append((lid,'caregist', 'https://www.caregist.co.uk/search?'+urllib.parse.urlencode(query)))
 if rating: query['rating']=rating
 else: query['opportunity']='not_yet_inspected'
 items.append((lid,'filtered','https://www.caregist.co.uk/search?'+urllib.parse.urlencode(query)))
with ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(fetch,items))
(P/'requests.json').write_text(json.dumps(results,indent=2))
print('requests',len(results),'errors',sum('error' in r for r in results))
