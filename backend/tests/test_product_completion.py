import hashlib
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy import select,func
from test_api import client,account,restaurant
from app.database import Session,User,AuthSession,SecurityToken,RateLimit,OwnershipProof,Restaurant

def test_attribution_is_scoped_deduplicated_and_private(client):
    auth=account(client);other=account(client,'attribution-other@example.test')
    result=client.post('/search',headers=auth,json={'query':'Chinese'}).json()
    rid=result['results'][0]['restaurant']['id'];token=result['attribution']
    for _ in range(2):assert client.post(f'/restaurants/{rid}/click',headers=auth,json={'attribution':token}).status_code==200
    assert client.post(f'/restaurants/{rid}/click',headers=other,json={'attribution':token}).status_code==403
    assert client.post(f'/restaurants/{rid}/click',headers=auth,json={'attribution':'forged'}).status_code==400
    funnel=client.get('/insights').json()['funnel']
    assert funnel['searches_with_click']==1 and funnel['conversion_percent']==100
    client.delete('/me/history',headers=auth)
    assert client.get('/insights').json()['funnel']['searches_with_click']==0


def test_owner_aggregate_performance_and_popular_recommendations(client):
    owner=account(client,'performance-owner@example.test','owner');rid=restaurant(client,owner)
    client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':'Hakka noodles','cuisine':'Chinese','price_paise':25000})
    customer=account(client)
    result=client.post('/search',headers=customer,json={'query':'Hakka noodles','include_samples':False}).json()
    assert client.post(f'/restaurants/{rid}/click',headers=customer,json={'attribution':result['attribution']}).status_code==200
    report=client.get(f'/portal/restaurants/{rid}/performance',headers=owner).json()
    assert report['funnel']['searches_with_results']==1 and report['funnel']['searches_with_click']==1
    assert 'Hakka noodles' not in str(report)
    assert client.get(f'/portal/restaurants/{rid}/performance',headers=customer).status_code==403
    assert client.get('/popular-dishes?include_samples=false').json()[0]['restaurant']['id']==rid
    recommendations=client.get('/me/recommendations?include_samples=false',headers=customer).json()
    assert recommendations[0]['restaurant']['id']==rid


def test_reset_tokens_are_one_use_and_revoke_all_sessions(client,monkeypatch):
    import app.account_security as security
    monkeypatch.setattr(security,'mail_enabled',lambda:True)
    sent=[];monkeypatch.setattr(security,'send_security_email',lambda email,purpose,token:sent.append((email,purpose,token)))
    auth=account(client)
    assert client.post('/auth/forgot-password',json={'email':'food@example.test'}).status_code==202
    assert client.post('/auth/forgot-password',json={'email':'missing@example.test'}).status_code==202
    assert len(sent)==1
    value=sent[0][2]
    with Session() as db:
        row=db.get(SecurityToken,hashlib.sha256(value.encode()).hexdigest());assert row and row.id!=value
    body={'token':value,'password':'new-secure-test-password'}
    assert client.post('/auth/reset-password',json=body).status_code==200
    assert client.get('/me',headers=auth).status_code==401
    assert client.post('/auth/reset-password',json=body).status_code==400
    assert client.post('/auth/login',json={'email':'food@example.test','password':'secure-test-password'}).status_code==401
    assert client.post('/auth/login',json={'email':'food@example.test','password':'new-secure-test-password'}).status_code==200


def test_email_verification_and_expiry(client,monkeypatch):
    import app.account_security as security
    sent=[];monkeypatch.setattr(security,'send_security_email',lambda email,purpose,token:sent.append(token))
    auth=account(client)
    assert client.post('/me/request-verification',headers=auth).status_code==200
    assert client.post('/auth/verify-email',json={'token':sent[-1]}).status_code==200
    assert client.get('/me',headers=auth).json()['email_verified']
    assert client.post('/auth/verify-email',json={'token':sent[-1]}).status_code==400


def test_persistent_auth_throttling(client):
    for _ in range(8):assert client.post('/auth/login',json={'email':'attack@example.test','password':'bad'}).status_code==401
    response=client.post('/auth/login',json={'email':'attack@example.test','password':'bad'})
    assert response.status_code==429 and response.headers['retry-after']=='300'
    with Session() as db:assert db.scalar(select(func.count()).select_from(RateLimit))>0


def test_dns_verification_and_domain_change_revokes_badge(client,monkeypatch):
    import httpx
    owner=account(client,'dns-owner@example.test','owner');rid=restaurant(client,owner)
    details={'name':'DNS Kitchen','address':'Bandra test Mumbai','area':'Bandra','latitude':19.0596,'longitude':72.8295,'cuisine':'Chinese','website':'https://kitchen.example.test'}
    assert client.put(f'/portal/restaurants/{rid}',headers=owner,json=details).status_code==200
    challenge=client.post(f'/portal/restaurants/{rid}/ownership-challenge',headers=owner).json()
    original=httpx.AsyncClient
    def handler(request):return httpx.Response(200,json={'Answer':[{'type':16,'data':'"'+challenge['record_value']+'"'}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    assert client.post(f'/portal/restaurants/{rid}/verify-ownership',headers=owner).json()['verified']
    assert client.get(f'/restaurants/{rid}').json()['restaurant']['ownership_verified']
    assert client.put(f'/portal/restaurants/{rid}',headers=owner,json={**details,'website':'https://other.example.test'}).status_code==200
    assert not client.get(f'/restaurants/{rid}').json()['restaurant']['ownership_verified']


def test_approved_link_discovery_and_menu_classification(monkeypatch):
    from app.discovery import menu_candidates,classify
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menu.example.test')
    html='<a href="/menu">Food</a><a href="https://evil.example/menu">Bad</a><a href="/menu.pdf">PDF</a>'
    assert menu_candidates(html,'https://menu.example.test')==['https://menu.example.test/menu']
    assert classify('Mango lassi')=='Drinks'


def test_health_remains_responsive_while_search_database_work_is_waiting(client,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    import app.main as main
    entered=threading.Event();release=threading.Event();original=main.search_database
    def waiting(*args):
        entered.set()
        assert release.wait(10)
        return original(*args)
    monkeypatch.setattr(main,'search_database',waiting)
    with ThreadPoolExecutor(max_workers=2) as pool:
        search=pool.submit(client.post,'/search',json={'query':'Chinese'})
        assert entered.wait(3)
        try:
            health=pool.submit(client.get,'/health')
            assert health.result(timeout=2).status_code==200
        finally:release.set()
        assert search.result(timeout=5).status_code==200


def test_unpriced_catalog_does_not_issue_one_query_per_restaurant(client):
    from sqlalchemy import event
    from app.database import engine
    from app.main import unpriced_nearby
    with Session() as db:
        for number in range(80):db.add(Restaurant(name=f'Unpriced fixture {number}',address='Bandra test fixture',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese'))
        db.commit()
    queries=[]
    def record(connection,cursor,statement,*args):
        if statement.lstrip().upper().startswith('SELECT'):queries.append(statement)
    event.listen(engine,'before_cursor_execute',record)
    try:
        with Session() as db:rows=unpriced_nearby(db,19.0596,72.8295,2)
        assert len(rows)==20
        assert len(queries)<=2
    finally:event.remove(engine,'before_cursor_execute',record)
