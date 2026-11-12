"""Documented keyless API consumer: serial requests, <=100/min, checkpointed facts only."""
import argparse,json,time,hashlib,re,unicodedata,collections,email.utils
from pathlib import Path
from datetime import datetime,timezone
import httpx
from shapely.geometry import shape,Point
from shapely.ops import unary_union
from app.city_catalog import normalized_name,metres
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--catalog',required=True,help='JSON export of canonical BiteAI public restaurant metadata')
parser.add_argument('--boundary',required=True,help='Mumbai district GeoJSON')
parser.add_argument('--output',required=True)
parser.add_argument('--requests-per-minute',type=int,default=90)
args=parser.parse_args()
if not 1<=args.requests_per_minute<=100:raise ValueError('Use 1–100 requests/minute, below the provider ceiling of 120')
ROOT=Path(args.output);ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'menus').mkdir(exist_ok=True)
existing=json.loads(Path(args.catalog).read_text())
by_name=collections.defaultdict(dict);by_phone=collections.defaultdict(dict)
def phone(v):
 d=re.sub(r'\D','',v or '');return d[-10:] if len(d)>=10 else ''
def core(v):
 return ' '.join(w for w in re.findall(r'\w+',unicodedata.normalize('NFKC',v).casefold()) if w not in {'hotel','restaurant','restaurants','bar','cafe','café','and','the','kitchen'})
for r in existing:
 by_name[normalized_name(r['name'])][r['source_id']]=r
 if phone(r.get('phone')):by_phone[phone(r.get('phone'))][r['source_id']]=r
region=unary_union([shape(f['geometry']) for f in json.loads(Path(args.boundary).read_text())['features']])
def match(hit):
 lat,lon=hit.get('lat'),hit.get('lon')
 if not isinstance(lat,(float,int)) or not isinstance(lon,(float,int)) or not region.covers(Point(lon,lat)):return None,'outside_boundary_or_missing_point'
 row={'latitude':lat,'longitude':lon};candidates=[]
 for r in by_name[normalized_name(hit.get('name',''))].values():
  d=metres(row,r)
  if d<=80:candidates.append((d,r,'exact_name_within_80m'))
 if not candidates and phone(hit.get('phone')):
  for r in by_phone[phone(hit.get('phone'))].values():
   d=metres(row,r)
   if d<=150 and core(r['name']) and core(r['name'])==core(hit.get('name','')):candidates.append((d,r,'same_phone_and_brand_within_150m'))
 if not candidates:return None,'unmatched_identity'
 candidates.sort(key=lambda v:v[0])
 if len(candidates)>1 and candidates[1][0]-candidates[0][0]<15:return None,'ambiguous_nearby_branches'
 d,r,method=candidates[0]
 return {'canonical_source_id':r['source_id'],'canonical_name':r['name'],'distance_m':round(d,2),'match_method':method},'matched'
statepath=ROOT/'collection-state.json'
state=json.loads(statepath.read_text()) if statepath.exists() else {'offset':0,'pages':0,'counts':{},'completed':False}
counts=collections.Counter();seen=set()
for path in (ROOT/'provider-hits.jsonl',):
 if path.exists():
  for line in path.open():
   record=json.loads(line);seen.add(record['id']);counts['listed_records']+=1;counts[record['match_status']]+=1
for file in (ROOT/'menus').glob('*.json'):
 try:
  menu=json.loads(file.read_text());counts['menus_downloaded']+=1
  counts['menu_items_received']+=sum(len(section['items']) for section in menu['menu']['sections'])
 except (ValueError,KeyError):file.unlink()
last=0.;origin='https://indiarestros.com';headers={'User-Agent':'BiteAI-Catalog/0.2 (documented public API; attributed menu facts only)'}
with httpx.Client(timeout=30,headers=headers,follow_redirects=False) as client:
 def get(path,params=None):
  global last
  for attempt in range(3):
   time.sleep(max(0,60/args.requests_per_minute-(time.monotonic()-last)));last=time.monotonic()
   response=client.get(origin+path,params=params)
   if response.status_code==429:
    retry=response.headers.get('Retry-After','60')
    try:delay=max(1,float(retry))
    except ValueError:
     try:delay=max(1,(email.utils.parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())
     except Exception:delay=60
    print('Rate limited; pausing',delay,'seconds',flush=True);time.sleep(delay);continue
   if response.status_code>=500 and attempt<2:time.sleep(3);continue
   response.raise_for_status()
   if len(response.content)>3_000_000 or 'json' not in response.headers.get('content-type',''):raise ValueError('Invalid or oversized API response')
   return response,response.json()
  raise RuntimeError('Provider rate limit persists; stopping collection')
 while not state.get('completed'):
  offset=state['offset'];response,payload=get('/api/v1/restaurants',{'city':'mumbai','limit':50,'offset':offset})
  hits=payload.get('results');following=payload.get('next_offset')
  if not isinstance(hits,list) or len(hits)>50:raise ValueError('Unexpected restaurant page')
  if following is not None and (not isinstance(following,int) or following<=offset):raise ValueError('Pagination did not advance')
  for hit in hits:
   rid=hit.get('id','')
   if not re.fullmatch(r'IRR-[A-Z0-9]{10}',rid):raise ValueError('Invalid provider ID')
   identity,reason=match(hit)
   if rid not in seen:
    seen.add(rid);counts['listed_records']+=1;counts[reason]+=1
    minimal={k:hit.get(k) for k in ('id','name','lat','lon','locality','menu_items','cuisines','url')}
    minimal.update(identity or {});minimal['match_status']=reason
    with (ROOT/'provider-hits.jsonl').open('a') as f:f.write(json.dumps(minimal,ensure_ascii=False)+'\n')
   if not identity or not isinstance(hit.get('menu_items'),int) or hit['menu_items']<=0:continue
   file=ROOT/'menus'/(rid+'.json')
   if file.exists():continue
   try:
    raw,menu=get('/api/v1/restaurants/'+rid+'/menu')
    if menu.get('restaurant')!=rid or not isinstance(menu.get('sections'),list):raise ValueError('Menu identity or schema mismatch')
    sections=[]
    for section in menu['sections']:
     sections.append({'name':section.get('name'),'items':[{k:item.get(k) for k in ('name','price','veg','dish','currency')} for item in section.get('items',[]) if isinstance(item,dict)]})
    facts={k:menu.get(k) for k in ('restaurant','name','url','source','source_url','updated','currency')}
    facts['sections']=sections
    snapshot={'provider':'IndiaRestros','api_url':str(raw.request.url),'retrieved_at':datetime.now(timezone.utc).isoformat(),'content_hash':hashlib.sha256(raw.content).hexdigest(),
     'identity':identity,'listing':{k:hit.get(k) for k in ('id','name','lat','lon','locality','cuisines','menu_items','url')},'menu':facts}
    file.write_text(json.dumps(snapshot,ensure_ascii=False));counts['menus_downloaded']+=1
    counts['menu_items_received']+=sum(len(s['items']) for s in sections)
   except (httpx.HTTPStatusError,httpx.RequestError,ValueError) as exc:
    counts['menu_fetch_errors']+=1
    with (ROOT/'errors.jsonl').open('a') as f:f.write(json.dumps({'id':rid,'error':type(exc).__name__,'status':getattr(getattr(exc,'response',None),'status_code',None)})+'\n')
  state.update(offset=following if following is not None else offset,pages=state['pages']+1,counts=dict(counts),completed=following is None or not hits,checked_at=datetime.now(timezone.utc).isoformat())
  temporary=statepath.with_suffix('.tmp');temporary.write_text(json.dumps(state,indent=2));temporary.replace(statepath)
  if state['pages']%10==0 or state['completed']:print(json.dumps(state),flush=True)
  if state['pages']>1200:raise RuntimeError('Review required: city pagination exceeded expected range')
print('Collection completed',json.dumps(state),flush=True)
