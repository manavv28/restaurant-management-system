import hashlib,hmac,json
from datetime import datetime,timedelta,timezone
import httpx
from sqlalchemy import select
from test_api import client,account,restaurant
from app.database import Session,DealVoucher,PaymentOrder,Transaction,User,Campaign,Redemption


def setup(client,monkeypatch,budget=200000):
    buyer=account(client);merchant=account(client,'voucher-owner@example.test','owner');rid=restaurant(client,merchant)
    client.put('/me/consent',headers=buyer,json={'consent':True})
    now=datetime.now(timezone.utc)
    c=client.post(f'/portal/restaurants/{rid}/campaigns',headers=merchant,json={'title':'Real logic test deal','percent':10,'max_discount_paise':5000,'min_order_paise':20000,'daily_budget_paise':budget,'starts_at':now.isoformat(),'ends_at':(now+timedelta(days=2)).isoformat()})
    assert c.status_code==200,c.text
    for k,v in {'RAZORPAY_KEY_ID':'rzp_test_voucher','RAZORPAY_KEY_SECRET':'fixture','RAZORPAY_WEBHOOK_SECRET':'fixture-secret','RAZORPAY_RESTAURANT_IDS':str(rid)}.items():monkeypatch.setenv(k,v)
    original=httpx.AsyncClient;counter=[]
    def handler(request):
        counter.append(1);data=json.loads(request.content)
        return httpx.Response(200,json={'id':'order_Voucher'+str(len(counter)),'amount':data['amount'],'currency':'INR'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    return buyer,merchant,rid,c.json()['id']


def signed(client,event,entity):
    key='refund' if event=='refund.processed' else 'payment'
    raw=json.dumps({'event':event,'payload':{key:{'entity':entity}}}).encode()
    return client.post('/payments/webhook',content=raw,headers={'x-razorpay-signature':hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest()})


def test_voucher_capture_qr_owner_isolation_replay_and_refund(client,monkeypatch):
    buyer,merchant,rid,cid=setup(client,monkeypatch)
    result=client.post('/payments/orders',headers=buyer,json={'restaurant_id':rid,'amount_paise':30000,'campaign_id':cid});assert result.status_code==200,result.text
    order=result.json();assert order['amount_paise']==27000 and order['test_mode']
    voucher=client.get('/me/vouchers',headers=buyer).json()[0];assert voucher['state']=='pending' and voucher['code'] is None
    assert client.get('/me/vouchers/'+voucher['id']+'/qr',headers=buyer).status_code==404
    capture={'id':'pay_VoucherCapture','order_id':order['order_id'],'amount':27000,'currency':'INR','status':'captured'}
    assert signed(client,'payment.captured',capture).json()['status']=='verified'
    assert signed(client,'payment.captured',capture).json()['status']=='duplicate'
    voucher=client.get('/me/vouchers',headers=buyer).json()[0];assert voucher['state']=='issued' and voucher['code']
    qr=client.get('/me/vouchers/'+voucher['id']+'/qr',headers=buyer);assert qr.status_code==200 and '<svg' in qr.text
    assert 'no-store' in qr.headers['cache-control']
    me=client.get('/me',headers=buyer).json();assert me['verified_spend_paise']==0
    assert me['rewards']['sandbox_spend_30d_paise']==27000
    other=account(client,'wrong-merchant@example.test','owner')
    assert client.post('/portal/vouchers/redeem',headers=other,json={'code':voucher['code']}).status_code==403
    assert client.post('/portal/vouchers/redeem',headers=merchant,json={'code':voucher['code']}).status_code==200
    assert client.post('/portal/vouchers/redeem',headers=merchant,json={'code':voucher['code']}).status_code==409
    assert signed(client,'refund.processed',{'id':'rfnd_Voucher','payment_id':'pay_VoucherCapture','amount':1000,'currency':'INR'}).json()['status']=='adjusted'
    assert client.get('/me/vouchers',headers=buyer).json()[0]['state']=='revoked'
    assert client.post('/portal/vouchers/redeem',headers=merchant,json={'code':voucher['code']}).status_code==409


def test_cancelled_unpaid_reservation_releases_budget_and_late_capture_fails_closed(client,monkeypatch):
    buyer,merchant,rid,cid=setup(client,monkeypatch,budget=3000)
    body={'restaurant_id':rid,'amount_paise':30000,'campaign_id':cid}
    order=client.post('/payments/orders',headers=buyer,json=body).json()
    assert client.post('/payments/orders',headers=buyer,json=body).status_code==403
    assert client.post('/payments/orders/'+order['order_id']+'/cancel',headers=buyer,json={}).status_code==200
    assert client.post('/payments/orders',headers=buyer,json=body).status_code==200
    assert signed(client,'payment.captured',{'id':'pay_Late','order_id':order['order_id'],'amount':27000,'currency':'INR','status':'captured'}).status_code==409
    with Session() as db:assert db.scalars(select(Transaction)).all()==[]


def test_live_keys_cannot_enable_real_charges(client,monkeypatch):
    buyer,merchant,rid,cid=setup(client,monkeypatch)
    monkeypatch.setenv('RAZORPAY_KEY_ID','rzp_live_not_authorized')
    assert not client.get('/payments/availability/'+str(rid)).json()['enabled']
    assert client.post('/payments/orders',headers=buyer,json={'restaurant_id':rid,'amount_paise':30000}).status_code==503
