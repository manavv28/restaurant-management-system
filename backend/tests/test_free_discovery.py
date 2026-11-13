"""Regression checks for free discovery, evidence honesty and safe worker recovery."""
import asyncio,json
from datetime import datetime,timedelta,timezone
import httpx
import pytest
from sqlalchemy import select
from test_api import client,account,restaurant
from app.agents import parse_local,Intent,understand
from app.saarthi import continued_intent
from app.catalog_worker import retry_delay_hours,schedule
from app.database import Session,MenuItem,User,CatalogSource,CatalogJob


def test_exclusions_and_group_budget_parsing():
    intent=parse_local('Chinese chahiye, noodles nahi, under 300 for 2 km')
    assert intent.cuisine=='Chinese' and intent.dish is None and intent.excluded_dishes==['noodles']
    assert intent.max_budget==300 and intent.radius_km==2
    assert parse_local('Chinese for 2 km').max_budget==500
    intent=parse_local('hakka noodles for two people under 300 total delivery')
    assert intent.party_size==2 and intent.budget_scope=='total' and intent.max_budget==300
    assert parse_local('no Chinese, pizza under 400').cuisine is None


def test_context_preserves_exclusions_and_explicit_location():
    previous=parse_local('Chinese under 300 within 2 km in Bandra').model_dump()
    updated=continued_intent('same budget, Andheri mein, noodles nahi',parse_local('same budget, Andheri mein, noodles nahi'),previous)
    assert updated.cuisine=='Chinese' and updated.location=='Andheri'
    assert updated.excluded_dishes==['noodles'] and updated.max_budget==300 and updated.radius_km==2


def test_exclusions_and_total_budget_filter_real_results(client):
    rows=client.post('/search',json={'query':'Chinese no noodles under 300'}).json()['results']
    assert rows and all('noodles' not in row['dish']['name'].lower() for row in rows)
    # One 240-rupee item cannot fit an assumption of two items within 300 total.
    assert not client.post('/search',json={'query':'hakka noodles for two people under 300 total'}).json()['results']
    data=client.post('/search',json={'query':'hakka noodles for two people under 500 total delivery'}).json()
    price=data['results'][0]['budget_breakdown']
    assert price['listed_subtotal_paise']==48000 and price['quantity']==2
    assert price['payable_total_paise'] is None and price['taxes_paise'] is None
    assert price['status']=='unconfirmed' and 'unconfirmed' in data['verdict']['headline']


def test_explicit_area_overrides_stale_gps(client):
    data=client.post('/search',json={'query':'pizza in Andheri','latitude':19.0596,'longitude':72.8295}).json()
    origin=data['trace'][1]['output']
    assert origin['area']=='Andheri' and origin['latitude']==19.1197 and origin['origin']=='area centre'


def test_walking_and_payment_limits_are_visible(client):
    data=client.post('/search',json={'query':'Hakka noodles walking distance'}).json()
    assert 'Walking distance could not be verified' in data['verdict']['distance_notice']
    assert client.get('/health').json()['payment_history_access'] is False
    auth=account(client)
    consent=client.put('/me/consent',headers=auth,json={'consent':True}).json()
    assert consent['retention_days']==365 and 'no GPay' in consent['scope']


def test_free_local_model_adapter_validates_schema_and_falls_back(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False);monkeypatch.setenv('OLLAMA_URL','http://127.0.0.1:11434')
    original=httpx.AsyncClient
    def handler(request):
        body=json.loads(request.content);assert body['stream'] is False and body['format']['type']=='object'
        return httpx.Response(200,json={'message':{'content':json.dumps({'dish':'hakka noodles','max_budget':275})}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    intent,parser=asyncio.run(understand('noodles under 300',500,5))
    assert intent.max_budget==300 and intent.dish=='hakka noodles' and parser=='Local model structured extraction'
    def invalid(request):return httpx.Response(200,json={'message':{'content':'{"max_budget":-1}'}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(invalid),**kw))
    intent,parser=asyncio.run(understand('noodles under 300',500,5))
    assert intent.max_budget==300 and 'unavailable' in parser


def test_http_date_retry_after_and_backoff():
    request=httpx.Request('GET','https://example.test/menu')
    from email.utils import format_datetime
    response=httpx.Response(429,headers={'Retry-After':format_datetime(datetime.now(timezone.utc)+timedelta(hours=2))},request=request)
    error=httpx.HTTPStatusError('rate limited',request=request,response=response)
    assert 1.9<retry_delay_hours(error,1)<=2.01
    assert retry_delay_hours(ValueError('temporary'),1)==1/60
    assert retry_delay_hours(ValueError('temporary'),3)==4/60


def test_failed_sources_have_cooldown_and_admin_only_recovery(client):
    with Session() as db:
        source=CatalogSource(kind='approved_menu',url='https://menu.example.test/menu',area='Bandra',permission_note='Reviewed fixture',refresh_hours=24)
        db.add(source);db.flush()
        job=CatalogJob(source_id=source.id,state='failed',attempts=3,error='No unambiguous INR menu items extracted',finished_at=(datetime.now(timezone.utc)-timedelta(hours=7)).isoformat(),available_at='2000')
        db.add(job);db.commit();jid=job.id
        assert schedule(db)==0
    wall=client.get('/agents/activity').json()
    assert wall['source_health']['failure_categories']['extraction_or_identity']==1
    assert 'example.test' not in json.dumps(wall)
    auth=account(client)
    assert client.get('/admin/catalog/jobs',headers=auth).status_code==403
    with Session() as db:db.scalar(select(User)).role='admin';db.commit()
    assert client.post(f'/admin/catalog/jobs/{jid}/retry',headers=auth).json()['state']=='queued'
    assert client.post(f'/admin/catalog/jobs/{jid}/retry',headers=auth).status_code==409


def test_context_changes_food_without_inheriting_old_cuisine():
    previous=parse_local('Chinese hakka noodles under 300 within 2 km').model_dump()
    changed=continued_intent('same budget, pizza instead',parse_local('same budget, pizza instead'),previous)
    assert changed.dish=='pizza' and changed.cuisine is None and changed.max_budget==300
    changed=continued_intent('same budget Italian',parse_local('same budget Italian'),previous)
    assert changed.cuisine=='Italian' and changed.dish is None


def test_ambiguous_alternative_dish_is_not_an_exact_match(client):
    owner=account(client,'variant-owner@example.test','owner');rid=restaurant(client,owner)
    client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':'Fried Rice / Hakka noodles / Chopsuey','cuisine':'Chinese','price_paise':10000})
    matches=client.post('/search',json={'query':'hakka noodles under 300'}).json()['results']
    assert all(row['restaurant']['id']!=rid for row in matches)
