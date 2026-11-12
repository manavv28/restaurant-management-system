"""Checkpointed, rate-limited reads for reviewed venues with missing business phones."""
import argparse,json,time,threading,hashlib,collections
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import httpx
from app.contact_enrichment import prepare_contact,operator_sql
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--targets',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.output);(root/'snapshots').mkdir(parents=True,exist_ok=True);(root/'sql').mkdir(exist_ok=True)
if (root/'publication.json').exists():raise ValueError('Published plan is immutable; use a new output directory')
targets=json.loads(Path(a.targets).read_text());lock=threading.Lock();last=0.;blocked=0.
with httpx.Client(timeout=25,follow_redirects=False,headers={'User-Agent':'BiteAI-Catalog/0.3 (permitted public business-contact facts)'}) as client:
 def collect(target):
  global last,blocked
  file=root/'snapshots'/(target['external_id']+'.json')
  if file.exists():return
  for attempt in range(3):
   with lock:
    time.sleep(max(0,.7-(time.monotonic()-last),blocked-time.monotonic()));last=time.monotonic()
   try:
    response=client.get('https://indiarestros.com/api/v1/restaurants/'+target['external_id'])
    if response.status_code==429:
     retry=response.headers.get('Retry-After','60');delay=int(retry) if retry.isdigit() else 60;deadline=time.monotonic()+delay
     with lock:blocked=max(blocked,deadline)
     continue
    response.raise_for_status()
    if len(response.content)>3_000_000:raise ValueError('Oversized public API response')
    doc=response.json();minimal={k:doc.get(k) for k in ('id','name','lat','lon','phones','updated','sources')}
    snapshot={'target':target,'document':minimal,'retrieved_at':datetime.now(timezone.utc).isoformat(),'content_hash':hashlib.sha256(response.content).hexdigest()}
    temporary=file.with_suffix('.tmp');temporary.write_text(json.dumps(snapshot,ensure_ascii=False));temporary.replace(file);return
   except (httpx.HTTPError,ValueError):
    if attempt==2:return
    time.sleep(2)
 with ThreadPoolExecutor(max_workers=4) as pool:
  for index,_ in enumerate(pool.map(collect,targets)):
   if index%25==0:print('Checked',index+1,'/',len(targets),flush=True)
accepted=[];rejections=collections.Counter();current_targets={t['external_id']:t for t in json.loads(Path(a.targets).read_text())}
for file in sorted((root/'snapshots').glob('*.json')):
 snapshot=json.loads(file.read_text())
 try:accepted.append(prepare_contact(snapshot['document'],current_targets[snapshot['target']['external_id']],snapshot['retrieved_at'],snapshot['content_hash']))
 except (ValueError,KeyError,TypeError) as e:rejections[str(e)[:120]]+=1
(root/'plan.json').write_text(json.dumps(accepted,ensure_ascii=False,separators=(',',':')))
for old in (root/'sql').glob('*.sql'):old.unlink()
for index,start in enumerate(range(0,len(accepted),50)):(root/'sql'/f'{index:03}.sql').write_text(operator_sql(accepted[start:start+50]))
report={'targets':len(targets),'snapshots':len(list((root/'snapshots').glob('*.json'))),'accepted_contacts':len(accepted),'rejections':dict(rejections),'plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'status':'Prepared only; not yet published. Public business contacts are unverified source observations.'}
(root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
