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
