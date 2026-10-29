from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,urllib.request,hashlib
from dotenv import dotenv_values
P=Path(__file__).parent
rows=json.loads((P/'sample.json').read_text())['rows']; key=dotenv_values('.env')['CQC_API_KEY']
def fetch(item):
 lid,kind,url=item;t=datetime.now(timezone.utc).isoformat()
 try:
  h={'User-Agent':'Mozilla/5.0 (compatible; CareGist evidence audit)'}
  if kind=='api':h['Ocp-Apim-Subscription-Key']=key
  with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=30) as r: b=r.read();status=r.status;final=r.url
  ext='json' if kind=='api' else 'html';f=P/'raw'/f'{lid}-{kind}.{ext}';f.write_bytes(b)
  return dict(id=lid,kind=kind,url=url,observed_at=t,status=status,final_url=final,path=str(f),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:return dict(id=lid,kind=kind,url=url,observed_at=t,error=str(e))
items=[]
for r in rows:
 lid=r['id'];items.extend([(lid,'detail','https://www.caregist.co.uk/provider/'+(r['slug'] or lid)),(lid,'api','https://api.service.cqc.org.uk/public/v1/locations/'+lid)])
with ThreadPoolExecutor(max_workers=4) as pool:result=list(pool.map(fetch,items))
(P/'identity-api-requests.json').write_text(json.dumps(result,indent=2));print('requests',len(result),'errors',sum('error' in x for x in result))
