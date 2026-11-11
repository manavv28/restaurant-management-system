import hashlib,hmac,json
from test_api import client,account,restaurant
from app.database import Session,PaymentOrder,Transaction
from sqlalchemy import select,func

def test_signed_capture_and_replay_never_double_counts(client,monkeypatch):
    auth=account(client)
    owner=account(client,'payment-owner@example.test','owner');rid=restaurant(client,owner)
    uid=client.get('/me',headers=auth).json()['id']
    client.put('/me/consent',headers=auth,json={'consent':True})
    with Session() as db:
        db.add(PaymentOrder(provider_order_id='order_Test123',user_id=uid,restaurant_id=rid,amount_paise=30000));db.commit()
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET','fixture-secret')
    data={'event':'payment.captured','payload':{'payment':{'entity':{'id':'pay_Test123','order_id':'order_Test123','amount':30000,'currency':'INR','status':'captured'}}}}
    raw=json.dumps(data).encode();signature=hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest()
    assert client.post('/payments/webhook',content=raw,headers={'x-razorpay-signature':'bad'}).status_code==401
    response=client.post('/payments/webhook',content=raw,headers={'x-razorpay-signature':signature})
    assert response.json()['status']=='verified'
    assert client.get('/me',headers=auth).json()['verified_spend_paise']==30000
    assert client.post('/payments/webhook',content=raw,headers={'x-razorpay-signature':signature}).json()['status']=='duplicate'
    with Session() as db:assert db.scalar(select(func.count()).select_from(Transaction))==1

def test_orders_fail_closed_without_onboarding(client):
    auth=account(client)
    assert client.post('/payments/orders',headers=auth,json={'restaurant_id':1,'amount_paise':30000}).status_code==403
    client.put('/me/consent',headers=auth,json={'consent':True})
    assert client.post('/payments/orders',headers=auth,json={'restaurant_id':1,'amount_paise':30000}).status_code==422

def test_mismatch_and_withdrawal_do_not_credit_spending(client,monkeypatch):
    auth=account(client)
    owner=account(client,'blocked-payment-owner@example.test','owner');rid=restaurant(client,owner)
    uid=client.get('/me',headers=auth).json()['id']
    with Session() as db:
        db.add(PaymentOrder(provider_order_id='order_Blocked',user_id=uid,restaurant_id=rid,amount_paise=30000));db.commit()
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET','fixture-secret')
    def send(amount):
        event={'event':'payment.captured','payload':{'payment':{'entity':{'id':'pay_Blocked','order_id':'order_Blocked','amount':amount,'currency':'INR','status':'captured'}}}}
        raw=json.dumps(event).encode()
        return client.post('/payments/webhook',content=raw,headers={'x-razorpay-signature':hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest()})
    assert send(20000).status_code==409
    assert send(30000).status_code==409
    assert client.get('/me',headers=auth).json()['verified_spend_paise']==0


def test_validated_provider_order_and_private_status(client,monkeypatch):
    import httpx
    auth=account(client)
    owner=account(client,'provider-owner@example.test','owner');rid=restaurant(client,owner)
    client.put('/me/consent',headers=auth,json={'consent':True})
    for key,value in {'RAZORPAY_KEY_ID':'rzp_test_fixture','RAZORPAY_KEY_SECRET':'fixture-key','RAZORPAY_WEBHOOK_SECRET':'fixture-webhook','RAZORPAY_RESTAURANT_IDS':str(rid)}.items():monkeypatch.setenv(key,value)
    original=httpx.AsyncClient
    seen=[]
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200,json={'id':'order_ProviderTest','amount':30000,'currency':'INR'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert client.get(f'/payments/availability/{rid}').json()['enabled']
    response=client.post('/payments/orders',headers=auth,json={'restaurant_id':rid,'amount_paise':30000})
    assert response.status_code==200,response.text
    assert seen[0]['amount']==30000 and seen[0]['currency']=='INR'
    assert client.get('/payments/orders/order_ProviderTest',headers=auth).json()['state']=='created'
    other=account(client,'provider-other@example.test')
    assert client.get('/payments/orders/order_ProviderTest',headers=other).status_code==404
    assert client.get('/me',headers=auth).json()['verified_spend_paise']==0


def test_malformed_signed_event_is_bad_request(client,monkeypatch):
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET','fixture-secret')
    for order_id in (None,123,[],{}):
        event={'event':'payment.captured','payload':{'payment':{'entity':{'id':'pay_Test','order_id':order_id,'amount':30000,'currency':'INR','status':'captured'}}}}
        raw=json.dumps(event).encode()
        response=client.post('/payments/webhook',content=raw,headers={'x-razorpay-signature':hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest()})
        assert response.status_code==400
