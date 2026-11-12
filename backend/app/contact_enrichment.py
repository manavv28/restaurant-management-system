"""Conservative business-contact facts from the documented, permitted public API."""
import hashlib,json,re
from datetime import datetime,timedelta,timezone
from .public_menu_api import name_key,source_date,validate_original_identity
from .agents import distance_km


def business_phone(value):
    if not isinstance(value,str):return None
    # Reject extensions, lists and free text; never assemble a number from unrelated digits.
    if re.search(r'[^0-9+() .-]',value) or value.count('+')>1:return None
    digits=re.sub(r'\D','',value)
    if len(digits)==12 and digits.startswith('91'):digits=digits[2:]
    elif len(digits)==11 and digits.startswith('0'):digits=digits[1:]
    if len(digits)!=10 or digits[0] not in '23456789' or len(set(digits))==1:return None
    return '+91'+digits


def prepare_contact(document,target,retrieved_at,content_hash):
    if not target.get('area'):raise ValueError('Canonical area required for branch review')
    if document.get('id')!=target['external_id'] or name_key(str(document.get('name','')))!=name_key(target['expected_name']):raise ValueError('Provider identity changed; review required')
    lat,lng=document.get('lat'),document.get('lon')
    if not isinstance(lat,(int,float)) or not isinstance(lng,(int,float)) or not 18.85<=lat<=19.35 or not 72.75<=lng<=73.05:raise ValueError('Missing Mumbai coordinates')
    if distance_km(lat,lng,target['latitude'],target['longitude'])*1000>80:raise ValueError('Provider branch moved; review required')
    observed=source_date(retrieved_at);updated=source_date(document.get('updated'))
    if not observed or not updated or updated>observed or datetime.fromisoformat(updated)<datetime.fromisoformat(observed)-timedelta(days=90):raise ValueError('Missing, future or old source date')
    if not re.fullmatch('[a-f0-9]{64}',content_hash):raise ValueError('Actual response hash required')
    # A merged provider record naming multiple brands is unsuitable for contact enrichment.
    for source in document.get('sources',[]):
        if isinstance(source,dict) and source.get('url'):
            validate_original_identity({'name':document['name'],'locality':target.get('area','')},source['url'])
    phones={}
    for raw in document.get('phones',[]):
        if not isinstance(raw,dict):continue
        number=business_phone(raw.get('v'));origin=raw.get('src')
        if number and isinstance(origin,str) and origin.strip():phones.setdefault(number,set()).add(origin[:80])
    if not phones:raise ValueError('No unambiguous public business phone')
    corroborated=[phone for phone,sources in phones.items() if len(sources)>=2]
    if len(corroborated)==1:phone=corroborated[0]
    elif len(phones)==1:phone=next(iter(phones))
    else:raise ValueError('Conflicting contact numbers; review required')
    evidence={'kind':'public_contact','phone':phone,'provider':'IndiaRestros','original_sources':sorted(phones[phone]),'source_url':'https://indiarestros.com/api/v1/restaurants/'+target['external_id'],'source_observed_at':updated,'retrieved_at':observed,'content_hash':content_hash,'status':'Public source listing; not independently verified'}
    return {'target_source_id':target['source_id'],'phone':phone,'observed_at':observed,'source_url':evidence['source_url'],'trace':json.dumps(evidence,ensure_ascii=False,separators=(',',':'))}

CONTACT_SQL="""
WITH input AS MATERIALIZED (SELECT * FROM jsonb_to_recordset(CAST(:contact_data AS jsonb)) AS x(target_source_id text,phone text,observed_at text,source_url text,trace text)),
updated AS (UPDATE restaurants r SET phone=x.phone,updated_at=x.observed_at FROM input x
 WHERE r.source_id=x.target_source_id AND NOT r.sample AND r.owner_id IS NULL AND trim(r.phone)=''
 RETURNING r.id,r.source_id,r.phone),
audits AS (INSERT INTO ingestion_logs(restaurant_id,source,trace,created_at)
 SELECT r.id,x.source_url,x.trace,x.observed_at FROM updated r JOIN input x ON x.target_source_id=r.source_id AND x.phone=r.phone RETURNING id)
SELECT (SELECT count(*) FROM updated) AS contacts_added,(SELECT count(*) FROM audits) AS evidence_rows;
"""

def operator_sql(contacts):
    if not 1<=len(contacts)<=50 or len({c['target_source_id'] for c in contacts})!=len(contacts):raise ValueError('Use 1–50 distinct reviewed venues')
    payload=json.dumps(contacts,ensure_ascii=False,separators=(',',':'));tag='$biteai_contact$'
    if tag in payload:raise ValueError('SQL delimiter collision')
    return CONTACT_SQL.replace('CAST(:contact_data AS jsonb)',tag+payload+tag+'::jsonb')

def public_contact(phone,trace):
    try:
        value=json.loads(trace)
        if value.get('kind')!='public_contact' or value.get('phone')!=phone:return None
        if not re.fullmatch(r'https://indiarestros\.com/api/v1/restaurants/IRR-[A-Z0-9]{10}',value.get('source_url','')):return None
        return {key:value[key] for key in ('provider','original_sources','source_url','source_observed_at','retrieved_at','status')}
    except (ValueError,TypeError,KeyError,AttributeError):return None
