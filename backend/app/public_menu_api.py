"""IndiaRestros documented public API: attributed price facts, no images/descriptions.

Terms permit personal/commercial reads at 120 requests/minute/IP. The supervised
worker processes at most five successful menus per 30-second loop, serially.
"""
import base64,hashlib,json,re,unicodedata
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit
import httpx
from sqlalchemy import text
from .catalog import paise

API_KIND='indiarestros_api'
METHOD='indiarestros-api/INR'
TERMS='https://indiarestros.com/terms'
PATTERN=r'https://indiarestros\.com/api/v1/restaurants/(IRR-[A-Z0-9]{10})/menu'

def provider_id(url):
    match=re.fullmatch(PATTERN,url)
    if not match:raise ValueError('Only documented IndiaRestros menu endpoints are allowed')
    return match[1]

def name_key(name):
    return ' '.join(unicodedata.normalize('NFKC',name).casefold().split())

def source_date(value):
    if not value:return None
    try:
        date=datetime.fromisoformat(value.replace('Z','+00:00'))
        if not date.tzinfo:return None
        return date.astimezone(timezone.utc).isoformat()
    except (ValueError,AttributeError):return None

def validate_original_identity(listing,original):
    """Reject an explicit conflicting brand or branch in a named upstream menu URL."""
    parsed=urlsplit(original);parts=[p for p in parsed.path.split('/') if p]
    slug=None
    if parsed.hostname in ('zomato.com','www.zomato.com') and len(parts)>=2:slug=parts[1]
    if parsed.hostname in ('magicpin.in','www.magicpin.in'):
        for index,part in enumerate(parts[:-1]):
            if part.casefold()=='restaurant':slug=parts[index+1];break
    if not slug:return
    stop={'the','and','by','of','for','a','an','restaurant','restaurants','cafe','café','hotel','bar','food','foods','kitchen','house','pure','veg','limited','branch','mumbai','bombay','east','west','north','south'}
    def words(value):return {w for w in re.findall(r'[^\W_]+',value.casefold().replace("'",'').replace('’','')) if len(w)>1}
    geography=words(str(listing.get('locality') or ''))
    brand=words(listing['name'])-stop-geography
    origin=words(slug)-stop-geography
    if brand and origin and not brand.intersection(origin):raise ValueError('Original menu names a different brand; review required')
    from .areas import AREAS
    def areas(value):
        value=' '+re.sub(r'[^\w]+',' ',value.casefold())+' '
        return {area for area in AREAS if ' '+area.casefold()+' ' in value}
    expected=areas(str(listing.get('locality') or ''));actual=areas(slug)
    if expected and actual and not expected.intersection(actual):raise ValueError('Original menu names a different area; review required')

def prepare_snapshot(snapshot):
    rid=provider_id(snapshot['api_url']);menu=snapshot['menu'];listing=snapshot['listing']
    if menu.get('restaurant')!=rid or listing.get('id')!=rid:raise ValueError('Provider identity mismatch')
    if name_key(menu.get('name',''))!=name_key(listing.get('name','')):raise ValueError('Menu/restaurant name mismatch')
    if menu.get('currency') not in (None,'INR'):raise ValueError('Menu currency is not INR')
    observed=source_date(snapshot.get('retrieved_at'))
    if not observed:raise ValueError('Actual API retrieval date required')
    updated=source_date(menu.get('updated'))
    if not updated:raise ValueError('Provider observation date required')
    if updated>observed:raise ValueError('Provider observation is in the future')
    original_deadline=datetime.fromisoformat(updated)+timedelta(days=90)
    if original_deadline<=datetime.fromisoformat(observed):raise ValueError('Provider menu observation older than 90 days; review required')
    public_url=menu.get('url','')
    if not re.fullmatch(r'https://indiarestros\.com/r/[a-zA-Z0-9%._~\-/]+/menu',public_url):raise ValueError('Invalid public menu reference')
    source=str(menu.get('source') or 'unspecified')[:80]
    original=menu.get('source_url') or ''
    parsed=urlsplit(original)
    if original and (parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password):raise ValueError('Invalid original source URL')
    validate_original_identity(listing,original)
    context='delivery listing' if '/order' in parsed.path.casefold() else 'listing; dine-in/delivery not specified'
    grouped={};rejected=0
    for section in menu.get('sections',[]):
        category=' '.join(str(section.get('name') or 'Main').split())[:80]
        for raw in section.get('items',[]):
            name=raw.get('name')
            if not isinstance(name,str):rejected+=1;continue
            name=' '.join(name.split())
            if not 2<=len(name)<=150 or raw.get('currency') not in (None,'INR') or raw.get('variants') or raw.get('price_range'):
                rejected+=1;continue
            try:price=paise(raw.get('price'))
            except ValueError:rejected+=1;continue
            key=name_key(name)
            row={'name':name,'category':category,'price_paise':price,'dietary':'vegetarian' if raw.get('veg') is True else None,
                 'source_key':'ir:'+base64.urlsafe_b64encode(hashlib.sha256((rid+'\n'+key).encode()).digest()).decode().rstrip('='),
                 'excerpt':json.dumps({'name':name,'price_paise':price,'currency':'INR','veg':raw.get('veg') if type(raw.get('veg')) is bool else None},ensure_ascii=False,separators=(',',':'))}
            grouped.setdefault(key,[]).append(row)
    items=[]
    for rows in grouped.values():
        if len({r['price_paise'] for r in rows})!=1:rejected+=len(rows);continue
        if any(row['dietary']!='vegetarian' for row in rows):rows[0]['dietary']=None
        items.append(rows[0])
    if not items:raise ValueError('No unambiguous positive INR price facts')
    if len(items)>2000:raise ValueError('Menu exceeds reviewed size limit')
    raw_cuisines=listing.get('cuisines') or []
    if not isinstance(raw_cuisines,list):raw_cuisines=[]
    raw_cuisines=[c for c in raw_cuisines if isinstance(c,str)][:10]
    cuisines=', '.join(c.replace('-',' ').title() for c in raw_cuisines)[:100] or 'Unspecified'
    metadata={'provider':'IndiaRestros','provider_id':rid,'expected_name':listing['name'],'provider_menu_url':public_url,
              'original_source':source,'original_url':original,'provider_updated_at':updated,'price_context':context,
              'retrieved_at':observed,'terms':TERMS,'permission':'Public API terms explicitly permit personal and commercial use',
              'identity_match':snapshot['identity'],'provider_latitude':listing.get('lat'),'provider_longitude':listing.get('lon'),'cuisines':raw_cuisines,'locality':listing.get('locality'),'currency_basis':'Documented menu API returns rupee prices'}
    digest=snapshot.get('content_hash','')
    if not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('Original response content hash required')
    return {'target_source_id':snapshot['identity']['canonical_source_id'],'provider_id':rid,'api_url':snapshot['api_url'],
            'public_url':public_url,'metadata':metadata,'content_hash':digest,'observed_at':observed,
            'expires_at':min(datetime.fromisoformat(observed)+timedelta(hours=48),original_deadline).isoformat(),
            'cuisine':cuisines,'items':items,'rejected_items':rejected}

async def fetch_snapshot(source,identity):
    rid=provider_id(source.url)
    async with httpx.AsyncClient(timeout=25,follow_redirects=False,headers={'User-Agent':'BiteAI-Catalog/0.2 (documented public API; attributed price facts)'}) as client:
        async with client.stream('GET',source.url) as response:
            response.raise_for_status()
            if response.is_redirect or 'json' not in response.headers.get('content-type',''):raise ValueError('Expected public API JSON')
            body=bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body)>3_000_000:raise ValueError('API menu exceeds size limit')
    document=json.loads(body)
    details=json.loads(identity.details)
    snapshot={'api_url':source.url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'content_hash':hashlib.sha256(body).hexdigest(),
              'identity':details['identity_match'],'listing':{'id':rid,'name':details['expected_name'],'cuisines':details.get('cuisines',[]),'locality':details.get('locality'),'lat':details.get('provider_latitude'),'lon':details.get('provider_longitude')},'menu':document}
    return prepare_snapshot(snapshot)

# Shared by the supervised worker and the reviewed offline operator import.
# All values are a bound JSONB parameter; no data becomes SQL identifiers.
BATCH_SQL="""
WITH capacity AS MATERIALIZED (SELECT pg_database_size(current_database()) < 445644800 AS within_budget),
input AS MATERIALIZED (
 SELECT * FROM jsonb_to_recordset(CAST(:snapshot_data AS jsonb)) AS x(
 target_source_id text,provider_id text,api_url text,public_url text,metadata jsonb,
 content_hash text,observed_at text,expires_at text,cuisine text,items jsonb)
), targets AS MATERIALIZED (
 SELECT r.id AS restaurant_id,r.area,x.* FROM restaurants r JOIN input x ON r.source_id=x.target_source_id
 WHERE r.owner_id IS NULL AND NOT r.sample AND (SELECT within_budget FROM capacity)
 AND NOT EXISTS(SELECT 1 FROM menu_items m JOIN menu_evidence e ON e.menu_item_id=m.id
 JOIN catalog_sources s ON s.id=e.source_id WHERE m.restaurant_id=r.id AND s.kind<>'indiarestros_api')
 AND NOT EXISTS(SELECT 1 FROM catalog_identities i WHERE i.provider='indiarestros' AND i.external_id=x.provider_id AND i.restaurant_id<>r.id)
 AND NOT EXISTS(SELECT 1 FROM catalog_sources s WHERE s.kind='indiarestros_api' AND s.restaurant_id=r.id AND (NOT s.enabled OR s.url<>x.api_url))
 ORDER BY r.id FOR UPDATE OF r
), identities AS (
 INSERT INTO catalog_identities(provider,external_id,restaurant_id,source_url,licence,observed_at,details)
 SELECT 'indiarestros',provider_id,restaurant_id,public_url,'IndiaRestros public API terms: https://indiarestros.com/terms',observed_at,metadata::text FROM targets
 ON CONFLICT(provider,external_id) DO UPDATE SET details=EXCLUDED.details,observed_at=EXCLUDED.observed_at
 WHERE catalog_identities.restaurant_id=EXCLUDED.restaurant_id RETURNING external_id,restaurant_id
), sources AS (
 INSERT INTO catalog_sources(kind,url,restaurant_id,area,permission_note,enabled,refresh_hours,checked_at)
 SELECT 'indiarestros_api',t.api_url,t.restaurant_id,t.area,t.metadata::text,true,24,t.observed_at
 FROM targets t JOIN identities i ON i.external_id=t.provider_id AND i.restaurant_id=t.restaurant_id
 ON CONFLICT(restaurant_id) WHERE kind='indiarestros_api' DO UPDATE
 SET permission_note=EXCLUDED.permission_note,checked_at=EXCLUDED.checked_at
 WHERE catalog_sources.enabled AND catalog_sources.url=EXCLUDED.url
 RETURNING id,restaurant_id,url
), incoming AS MATERIALIZED (
 SELECT s.id AS source_id,t.restaurant_id,t.public_url,t.cuisine,t.content_hash,t.observed_at,t.expires_at,
 i.source_key,i.name,i.category,i.price_paise,i.excerpt,i.dietary
 FROM targets t JOIN sources s ON s.restaurant_id=t.restaurant_id AND s.url=t.api_url
 CROSS JOIN LATERAL jsonb_to_recordset(t.items) AS i(source_key text,name text,category text,price_paise integer,excerpt text,dietary text)
 WHERE NOT EXISTS(SELECT 1 FROM menu_items old LEFT JOIN menu_evidence e ON e.menu_item_id=old.id
 WHERE old.restaurant_id=t.restaurant_id AND lower(old.name)=lower(i.name)
 AND (old.source_key IS NULL OR e.source_id IS DISTINCT FROM s.id))
), withdrawn_evidence AS (
 UPDATE menu_evidence e SET active=false FROM menu_items m
 WHERE e.menu_item_id=m.id AND e.source_id IN (SELECT id FROM sources)
 AND NOT EXISTS(SELECT 1 FROM incoming i WHERE i.source_key=m.source_key)
 RETURNING e.menu_item_id
), withdrawn_items AS (
 UPDATE menu_items m SET available=false WHERE m.id IN(SELECT menu_item_id FROM withdrawn_evidence) RETURNING id
), saved AS (
 INSERT INTO menu_items(restaurant_id,name,category,cuisine,price_paise,description,available,source,verified_at,source_key,dietary)
 SELECT restaurant_id,name,category,cuisine,price_paise,'',true,'IndiaRestros public menu listing',NULL,source_key,dietary FROM incoming
 ON CONFLICT(source_key) DO UPDATE SET name=EXCLUDED.name,category=EXCLUDED.category,cuisine=EXCLUDED.cuisine,
 price_paise=EXCLUDED.price_paise,available=true,source=EXCLUDED.source,dietary=EXCLUDED.dietary
 WHERE menu_items.restaurant_id=EXCLUDED.restaurant_id
 RETURNING id,source_key,restaurant_id
), evidence AS (
 INSERT INTO menu_evidence(menu_item_id,source_id,excerpt,content_hash,method,fetched_at,expires_at,active)
 SELECT m.id,i.source_id,i.excerpt,i.content_hash,'indiarestros-api/INR',i.observed_at,i.expires_at,true
 FROM saved m JOIN incoming i ON i.source_key=m.source_key
 ON CONFLICT(menu_item_id) DO UPDATE SET excerpt=EXCLUDED.excerpt,content_hash=EXCLUDED.content_hash,
 method=EXCLUDED.method,fetched_at=EXCLUDED.fetched_at,expires_at=EXCLUDED.expires_at,active=true
 WHERE menu_evidence.source_id=EXCLUDED.source_id
 RETURNING menu_item_id,source_id
), audits AS (
 INSERT INTO ingestion_logs(restaurant_id,source,trace,created_at)
 SELECT s.restaurant_id,s.url,jsonb_build_object('provider','IndiaRestros','listed_items',count(e.menu_item_id),'source_metadata',max(t.metadata::text)::jsonb,'content_hash',max(i.content_hash),
 'price_changes',coalesce(jsonb_agg(jsonb_build_object('menu_item_id',old.id,'before_paise',old.price_paise,'after_paise',i.price_paise))
 FILTER(WHERE old.id IS NOT NULL AND old.price_paise<>i.price_paise),'[]'::jsonb))::text,max(i.observed_at)
 FROM sources s JOIN targets t ON t.restaurant_id=s.restaurant_id AND t.api_url=s.url JOIN evidence e ON e.source_id=s.id JOIN saved m ON m.id=e.menu_item_id
 JOIN incoming i ON i.source_key=m.source_key LEFT JOIN menu_items old ON old.source_key=i.source_key
 GROUP BY s.restaurant_id,s.url RETURNING id
)
SELECT (SELECT count(*) FROM targets) AS eligible_restaurants,(SELECT count(*) FROM sources) AS menu_sources,
 (SELECT count(*) FROM saved) AS saved_items,(SELECT count(*) FROM evidence) AS evidence_items,
 (SELECT count(*) FROM withdrawn_items) AS withdrawn_items,(SELECT count(*) FROM audits) AS audit_rows,
 NOT (SELECT within_budget FROM capacity) AS storage_budget_reached;
"""

def persist_snapshots(db,snapshots):
    if db.bind.dialect.name!='postgresql':raise ValueError('Public API publication requires PostgreSQL')
    if not 1<=len(snapshots)<=20:raise ValueError('Publish 1–20 menus per transaction')
    if len({s['target_source_id'] for s in snapshots})!=len(snapshots):raise ValueError('One provider menu per restaurant per transaction')
    result=dict(db.execute(text(BATCH_SQL),{'snapshot_data':json.dumps(snapshots,ensure_ascii=False,separators=(',',':'))}).mappings().one())
    if result.pop('storage_budget_reached'):raise ValueError('Database storage budget reached; operator review required')
    return result

def operator_sql(snapshots):
    payload=json.dumps(snapshots,ensure_ascii=False,separators=(',',':'))
    tag='$biteai_public_menu$'
    if tag in payload:raise ValueError('SQL delimiter collision')
    return BATCH_SQL.replace('CAST(:snapshot_data AS jsonb)',tag+payload+tag+'::jsonb')
