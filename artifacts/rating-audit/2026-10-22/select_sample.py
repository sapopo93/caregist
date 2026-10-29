from pathlib import Path
from datetime import datetime,timezone
import json,psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import dotenv_values
P=Path(__file__).parent
c=psycopg2.connect(dotenv_values('.env')['DATABASE_URL']);c.set_session(readonly=True,isolation_level='REPEATABLE READ')
cols='id,name,slug,status,overall_rating,file_overall_rating,file_overall_rating_date,file_rating_source,file_rating_source_sha256,postcode,updated_at'
rows=[]
with c.cursor(cursor_factory=RealDictCursor) as q:
 q.execute("SELECT status,count(*) AS n,count(file_overall_rating) AS file_rated FROM care_providers GROUP BY status"); counts=list(q)
 for rating in ['Good','Requires improvement','Outstanding','Inadequate']:
  q.execute(f"SELECT {cols} FROM care_providers WHERE status='ACTIVE' AND coalesce(overall_rating,'')='' AND file_overall_rating=%s ORDER BY md5('caregist-rating-audit-2026-10-22:' || id),id LIMIT 5",(rating,))
  rows.extend(dict(r,stratum='file-backed '+rating) for r in q)
 q.execute(f"SELECT {cols} FROM care_providers WHERE status='ACTIVE' AND overall_rating IN ('Good','Requires improvement','Outstanding','Inadequate') AND file_overall_rating IS NOT NULL AND overall_rating<>file_overall_rating ORDER BY id")
 conflicts=list(q); rows.extend(dict(r,stratum='conflict') for r in conflicts)
 q.execute(f"SELECT {cols} FROM care_providers WHERE status='ACTIVE' AND coalesce(overall_rating,'')='' AND file_overall_rating IS NULL ORDER BY md5('caregist-rating-audit-2026-10-22:' || id),id LIMIT 5")
 rows.extend(dict(r,stratum='unrated') for r in q)
 q.execute("SELECT file_overall_rating, count(*) AS n FROM care_providers WHERE status='ACTIVE' AND coalesce(overall_rating,'')='' AND file_overall_rating IS NOT NULL GROUP BY 1");backed=list(q)
(P/'sample.json').write_text(json.dumps(dict(observed_at=datetime.now(timezone.utc).isoformat(),counts=counts,file_backed_counts=backed,conflict_count=len(conflicts),rows=rows),default=str,indent=2))
print('sample',len(rows),'conflicts',len(conflicts));print([(r['id'],r['stratum'],r['name']) for r in rows])
c.rollback();c.close()
