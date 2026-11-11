import os
import tempfile
from datetime import datetime, timedelta, timezone
os.environ['DATABASE_URL']=os.getenv('TEST_DATABASE_URL') or 'sqlite:///'+tempfile.mktemp(suffix='.sqlite')
os.environ['JWT_SECRET']='test-secret-only-abcdefghijklmnopqrstuvwxyz'
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.agents import parse_local, distance_km
from app.database import Session, Transaction, User, Search, Base, engine

import pytest

@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c: yield c

def account(c,email='food@example.test',role='customer'):
    response=c.post('/auth/register',json={'name':'Test person','email':email,'password':'secure-test-password','role':role})
    assert response.status_code==200, response.text
    return {'Authorization':'Bearer '+response.json()['token']}

def restaurant(c,h):
    r=c.post('/portal/restaurants',headers=h,json={'name':'Owner kitchen','address':'Owner supplied address Bandra Mumbai','area':'Bandra','latitude':19.0596,'longitude':72.8295,'cuisine':'Chinese'})
    assert r.status_code==200,r.text
    return r.json()['id']

def test_parser_and_distance():
    i=parse_local('Hakka noodles under ₹300 within 2 km in Bandra')
    assert (i.dish,i.max_budget,i.radius_km,i.location)==('hakka noodles',300,2,'Bandra')
    assert distance_km(19,72,19,72)==0
    assert 110 < distance_km(19,72,20,72) < 112

def test_search_database_filter_and_trace(client):
    r=client.post('/search',json={'query':'Chinese Hakka noodles under ₹300 within 2 km','area':'Bandra'}).json()
    assert len(r['results'])==1
    assert r['results'][0]['dish']['price_paise']==24000
    assert r['results'][0]['restaurant']['sample'] is True
    assert len(r['trace'])==5
    assert client.post('/search',json={'query':'Hakka noodles under ₹100','area':'Bandra'}).json()['results']==[]
    assert client.post('/search',json={'query':'Chinese','include_samples':False}).json()['results']==[]
    assert client.post('/search',json={'latitude':20,'longitude':72.8}).status_code==422

def test_auth_and_ownership(client):
    assert client.get('/me').status_code==401
    h=account(client)
    assert client.get('/me',headers=h).json()['name']=='Test person'
    assert client.post('/auth/login',json={'email':'food@example.test','password':'wrong'}).status_code==401
    assert client.post('/auth/login',json={'email':'food@example.test','password':'secure-test-password'}).status_code==200
    assert client.post('/portal/restaurants',headers=h,json={'name':'AA','address':'Bandra','area':'Bandra','latitude':19,'longitude':72.8,'cuisine':'Chinese'}).status_code==403
    o=account(client,'owner@example.test','owner');rid=restaurant(client,o)
    other=account(client,'other@example.test','owner')
    menu={'name':'Hakka noodles','cuisine':'Chinese','price_paise':25000}
    assert client.post(f'/portal/restaurants/{rid}/menu',headers=other,json=menu).status_code==403
    m=client.post(f'/portal/restaurants/{rid}/menu',headers=o,json=menu).json()
    assert client.put(f'/portal/restaurants/{rid}/menu/{m["id"]}',headers=o,json={**menu,'price_paise':20000}).status_code==200
    assert client.post('/search',json={'query':'Hakka noodles under ₹210','include_samples':False}).json()['results'][0]['dish']['price_paise']==20000

def test_consent_and_simulation_never_verified(client):
    h=account(client)
    assert client.post('/payments/simulate',headers=h,json={'restaurant_id':1,'amount_paise':200000}).status_code==403
    assert client.put('/me/consent',headers=h,json={'consent':True}).status_code==200
    t=client.post('/payments/simulate',headers=h,json={'restaurant_id':1,'amount_paise':200000})
    assert t.status_code==200 and t.json()['simulated']
    assert client.get('/me',headers=h).json()['verified_spend_paise']==0
    client.put('/me/consent',headers=h,json={'consent':False})
    assert client.post('/payments/simulate',headers=h,json={'restaurant_id':1,'amount_paise':20000}).status_code==403
    assert client.post('/payments/webhook').status_code==501

def test_discount_cap_audit_limit_and_minimum(client):
    h=account(client)
    assert client.post('/campaigns/1/redeem',headers=h,json={'order_paise':30000}).status_code==403
    for _ in range(5): assert client.post('/search',headers=h,json={'query':'Chinese'}).status_code==200
    assert client.get('/me/offers',headers=h).json()[0]['eligible']
    assert client.post('/campaigns/1/redeem',headers=h,json={'order_paise':1000}).status_code==422
    r=client.post('/campaigns/1/redeem',headers=h,json={'order_paise':999999})
    assert r.status_code==200,r.text
    assert r.json()['discount_paise']==10000
    assert 'eligibility' in r.json()['audit']
    assert client.post('/campaigns/1/redeem',headers=h,json={'order_paise':30000}).status_code==403
    assert len(client.get('/me/redemptions',headers=h).json())==1

def test_campaign_spending_visit_and_validity(client):
    o=account(client,'owner@example.test','owner');rid=restaurant(client,o)
    h=account(client)
    start=datetime.now(timezone.utc)
    campaign={'title':'Verified spend only','percent':10,'min_spend_paise':200000,'min_visits':2,'max_discount_paise':5000,'starts_at':start.isoformat(),'ends_at':(start+timedelta(days=1)).isoformat()}
    created=client.post(f'/portal/restaurants/{rid}/campaigns',headers=o,json=campaign)
    assert created.status_code==200,created.text
    cid=created.json()['id']
    assert client.post(f'/campaigns/{cid}/redeem',headers=h,json={'order_paise':30000}).status_code==403
    # Trusted fixture represents signature-verified provider records; no public API can create these.
    with Session() as db:
        uid=db.scalar(select(User.id).where(User.email=='food@example.test'))
        for n in range(2):db.add(Transaction(user_id=uid,restaurant_id=rid,amount_paise=100000,reference=f'PROVIDER-{n}',simulated=False))
        db.commit()
    assert client.post(f'/campaigns/{cid}/redeem',headers=h,json={'order_paise':30001}).json()['discount_paise']==3000
    bad={**campaign,'ends_at':(start-timedelta(days=1)).isoformat()}
    assert client.post(f'/portal/restaurants/{rid}/campaigns',headers=o,json=bad).status_code==422

def test_history_favourites_privacy(client):
    h=account(client);other=account(client,'someone@example.test')
    client.post('/search',headers=h,json={'query':'pizza'})
    assert len(client.get('/me/history',headers=h).json())==1
    assert client.get('/me/history',headers=other).json()==[]
    assert client.post('/me/favourites/1',headers=h).json()['saved']
    assert len(client.get('/me/favourites',headers=h).json())==1
    assert client.post('/me/favourites/1?menu_item_id=999',headers=h).status_code==404
    assert client.post('/me/favourites/1',headers=h).json()['saved'] is False
    client.delete('/me/history',headers=h)
    assert client.get('/me/history',headers=h).json()==[]

def test_provider_unavailable_and_analytics(client):
    o=account(client,'owner@example.test','owner');rid=restaurant(client,o)
    assert client.post('/portal/discover/Bandra',headers=o).status_code==503
    analytics=client.get(f'/portal/restaurants/{rid}/analytics',headers=o).json()
    assert 'query' not in analytics and analytics['restaurant_clicks']==0
    assert client.get('/health').json()['database']=='connected'

def test_retention(client):
    from app.jobs import retain
    with Session() as db:
        db.add(Search(query='old private query',budget=300,area='Bandra',results=0,trace='[]',created_at=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat()))
        db.commit()
    retain()
    with Session() as db: assert db.scalar(select(Search).where(Search.query=='old private query')) is None

def test_ingestion_deduplication_price_audit_and_constraints(client):
    from sqlalchemy.exc import IntegrityError
    from app.database import MenuItem
    o=account(client,'owner@example.test','owner');rid=restaurant(client,o)
    body={'source':'Owner approved menu export','permission_confirmed':True,'items':[{'name':'  Hakka  noodles ','cuisine':'Chinese','price_paise':25000}]}
    assert client.post(f'/portal/restaurants/{rid}/ingest',headers=o,json=body).status_code==200
    body['items'][0].update(name='Hakka noodles',price_paise=28000)
    response=client.post(f'/portal/restaurants/{rid}/ingest',headers=o,json=body)
    assert response.json()['trace'][1]['changes'][0]['previous_price_paise']==25000
    menu=client.get(f'/restaurants/{rid}').json()['menu']
    assert len(menu)==1 and menu[0]['price_paise']==28000
    assert len(client.get(f'/portal/restaurants/{rid}/ingestions',headers=o).json())==2
    with Session() as db:
        db.add(MenuItem(restaurant_id=rid,name='Bad price',cuisine='Chinese',price_paise=-1))
        with pytest.raises(IntegrityError):db.commit()
    assert client.post('/search',json={'query':'noodles under ₹0 within 0 km'}).status_code==422

def test_profile_preferences_and_no_cross_account_exposure(client):
    h=account(client)
    response=client.put('/me/profile',headers=h,json={'name':'New name','preferred_cuisine':'Italian'})
    assert response.status_code==200
    assert client.get('/me',headers=h).json()['preferred_cuisine']=='Italian'
    result=client.post('/search',headers=h,json={'query':''}).json()
    assert result['results'][0]['restaurant']['cuisine']=='Italian'
    assert client.put('/me/profile',headers=h,json={'name':'','preferred_cuisine':''}).status_code==422
