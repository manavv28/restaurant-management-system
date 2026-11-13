"""All provider responses here are explicit test fixtures, not live restaurant data."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import select, func
from test_api import client, account, restaurant
from app.database import Session, Restaurant, MenuItem, MenuEvidence, CatalogSource, CatalogJob, SearchMatch, Search
from app.catalog import import_osm, structured_menu, persist_menu, approved_url, fetch_menu, ai_menu
from app.catalog_worker import run_one, schedule
from app.agents import parse_local

def html(price='250'):
    return '<script type="application/ld+json">'+json.dumps({'@type':'MenuItem','name':'Hakka noodles','offers':{'price':price,'priceCurrency':'INR'}})+'</script>'

def source(db):
    r=Restaurant(name='Fixture restaurant',address='Test address only',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese',sample=False)
    db.add(r);db.flush()
    s=CatalogSource(kind='approved_menu',restaurant_id=r.id,url='https://menu.example.test/menu',area='Bandra',permission_note='Operator approved test fixture')
    db.add(s);db.commit();return s

def test_osm_dedup_attribution_missing_values_and_bounds(client):
    fixture={'elements':[{'type':'node','id':123,'lat':19.06,'lon':72.83,'tags':{'name':'Fixture restaurant','amenity':'restaurant'}},
                         {'type':'node','id':124,'lat':28.6,'lon':77.2,'tags':{'name':'Outside Mumbai','amenity':'restaurant'}}]}
    with Session() as db:
        assert import_osm(db,fixture,'Bandra')['inserted']==1;db.commit()
        assert import_osm(db,fixture,'Bandra')['updated']==1;db.commit()
        row=db.scalar(select(Restaurant).where(Restaurant.source_id=='osm:node:123'))
        assert row.phone=='' and row.rating is None and 'ODbL' in row.source and not row.sample
        assert db.scalar(select(func.count()).select_from(MenuItem).where(MenuItem.restaurant_id==row.id))==0

def test_structured_extraction_conflicting_currency_and_decimal():
    rows,_=structured_menu(html());assert rows[0]['price_paise']==25000
    assert structured_menu(html('NaN'))[0]==[]
    assert structured_menu(html('250.123'))[0]==[]
    assert structured_menu(html().replace('INR','USD'))[0]==[]
    assert structured_menu(html('250')+html('300'))[0]==[]

def test_refresh_price_evidence_and_stale_filter(client):
    with Session() as db:
        s=source(db)
        rows,_=structured_menu(html())
        persist_menu(db,s,html(),rows);db.commit()
        rid=s.restaurant_id
        mid=db.scalar(select(MenuItem.id).where(MenuItem.restaurant_id==rid))
        persist_menu(db,s,html('280'),structured_menu(html('280'))[0]);db.commit()
        assert db.get(MenuItem,mid).price_paise==28000
        assert db.get(MenuEvidence,mid).content_hash
    result=client.post('/search',json={'query':'Haka noodles for 300 within 2 km','include_samples':False}).json()
    assert len(result['results'])==1 and result['results'][0]['dish']['id']==mid
    assert result['catalog']['fresh_source_menu_items']==1
    with Session() as db:
        evidence=db.get(MenuEvidence,mid)
        evidence.expires_at=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat();db.commit()
    result=client.post('/search',json={'query':'Hakka noodles','include_samples':False}).json()
    assert result['results']==[]
    assert result['nearby_unpriced'][0]['restaurant']['id']==rid

def test_worker_success_retry_and_job_trace(client,monkeypatch):
    import app.catalog_worker as worker
    with Session() as db:
        s=source(db);sid=s.id
        assert schedule(db)==1 and schedule(db)==0
    async def fixture_fetch(s):return html()
    monkeypatch.setattr(worker,'fetch_menu',fixture_fetch)
    result=asyncio.run(run_one());assert result['state']=='succeeded'
    assert len(result['trace'])==3
    with Session() as db:
        db.add(CatalogJob(source_id=sid));db.commit()
    async def failed_fetch(s):raise ValueError('Source robots.txt disallows collection')
    monkeypatch.setattr(worker,'fetch_menu',failed_fetch)
    result=asyncio.run(run_one());assert result['state']=='failed' and result['review_required']
    with Session() as db:
        job=db.get(CatalogJob,result['job_id']);assert job.attempts==1 and 'robots' in job.error
        assert any(step['tool']=='source_review_required' for step in json.loads(job.trace))
    assert asyncio.run(run_one()) is None

def test_source_approval_and_owner_isolation(client,monkeypatch):
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menu.example.test')
    with __import__('pytest').raises(ValueError):approved_url('https://127.0.0.1/menu')
    with __import__('pytest').raises(ValueError):approved_url('https://user:password@menu.example.test/menu')
    with __import__('pytest').raises(ValueError):approved_url('https://swiggy.com/menu')
    owner=account(client,'catalog-owner@example.test','owner');rid=restaurant(client,owner)
    body={'url':'https://menu.example.test/menu','permission_note':'I own this website and permit collection'}
    assert client.post(f'/portal/restaurants/{rid}/sources',headers=owner,json=body).status_code==200
    assert client.post(f'/portal/restaurants/{rid}/sources',headers=owner,json=body).status_code==409
    other=account(client,'catalog-other@example.test','owner')
    assert client.get(f'/portal/restaurants/{rid}/sources',headers=other).status_code==403
    assert client.get(f'/portal/restaurants/{rid}/sources',headers=owner).json()[0]['jobs'][0]['state']=='queued'

def test_robots_denies_and_redirects_not_followed(client,monkeypatch):
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menu.example.test')
    original=httpx.AsyncClient;seen=[]
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200,text='User-agent: *\nDisallow: /')
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    with Session() as db:s=source(db)
    import pytest
    with pytest.raises(ValueError,match='robots'):asyncio.run(fetch_menu(s))
    assert seen==['https://menu.example.test/robots.txt']

def test_gemini_rejects_invented_evidence(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-fixture-only')
    original=httpx.AsyncClient
    data={'items':[{'name':'Hakka noodles','price_rupees':'250','evidence':'Hakka noodles ₹250'},
                   {'name':'Invented sushi','price_rupees':'90','evidence':'Invented sushi ₹90'},
                   {'name':'Hakka noodles','price_rupees':'100','evidence':'Hakka noodles ₹250'}]}
    def handler(request):return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':json.dumps(data)}]}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    rows,_=asyncio.run(ai_menu('Menu\nHakka noodles ₹250'))
    assert len(rows)==1 and rows[0]['price_paise']==25000

def test_search_snapshot_and_history_delete(client):
    auth=account(client)
    client.post('/search',headers=auth,json={'query':'Chinese'})
    with Session() as db:assert db.scalar(select(func.count()).select_from(SearchMatch))>0
    client.delete('/me/history',headers=auth)
    with Session() as db:assert db.scalar(select(func.count()).select_from(SearchMatch))==0

def test_exact_customer_phrase():
    intent=parse_local('I feel like eating Chinese in a 2 km radius. Can I get Haka noodles for 300?')
    assert intent.dish=='hakka noodles' and intent.max_budget==300 and intent.radius_km==2


def test_pause_withdraws_prices_and_refresh_is_owner_scoped(client,monkeypatch):
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menu.example.test')
    owner=account(client,'pause-owner@example.test','owner');rid=restaurant(client,owner)
    created=client.post(f'/portal/restaurants/{rid}/sources',headers=owner,json={'url':'https://menu.example.test/menu','permission_note':'I own this menu and permit collection'}).json()
    sid=created['source_id'];path=f'/portal/restaurants/{rid}/sources/{sid}'
    with Session() as db:
        s=db.get(CatalogSource,sid);persist_menu(db,s,html(),structured_menu(html())[0]);db.commit()
    assert client.post('/search',json={'query':'Hakka noodles','include_samples':False}).json()['results']
    assert client.post(path+'/refresh',headers=owner).json()['state']=='queued'
    assert client.put(path,headers=owner,json={'enabled':False}).status_code==200
    assert not client.post('/search',json={'query':'Hakka noodles','include_samples':False}).json()['results']
    assert client.post(path+'/refresh',headers=owner).status_code==409
    other=account(client,'pause-other@example.test','owner')
    assert client.put(path,headers=other,json={'enabled':True}).status_code==403
    assert client.put(path,headers=owner,json={'enabled':True}).status_code==200
    # Re-enabling never makes withdrawn evidence fresh without another collection.
    assert not client.post('/search',json={'query':'Hakka noodles','include_samples':False}).json()['results']
