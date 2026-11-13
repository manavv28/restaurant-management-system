"""Optional Razorpay orders and signed capture webhooks. No GPay history access."""
import hashlib
import hmac
import json
import os
import re
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from .database import PaymentOrder, Restaurant, Transaction, User, PaymentAdjustment, Campaign, Redemption, DealVoucher
from .schemas import TransactionInput
from .security import current_user, verified_user, db_session

router=APIRouter(prefix='/payments',tags=['Verified payments'])

@router.post('/orders')
async def create_order(body:TransactionInput,user=Depends(verified_user),db=Depends(db_session)):
    if not user.consent:raise HTTPException(403,'Payment-data consent is required')
    restaurant=db.get(Restaurant,body.restaurant_id)
    if not restaurant or restaurant.sample:raise HTTPException(422,'A real restaurant is required')
    if os.getenv('APP_ENV')=='production' and not restaurant.ownership_verified:raise HTTPException(503,'Restaurant website verification is incomplete')
    approved={v.strip() for v in os.getenv('RAZORPAY_RESTAURANT_IDS','').split(',')}
    if str(restaurant.id) not in approved:raise HTTPException(503,'Restaurant payment onboarding is incomplete')
    key,secret=os.getenv('RAZORPAY_KEY_ID'),os.getenv('RAZORPAY_KEY_SECRET')
    if not key or not secret or not os.getenv('RAZORPAY_WEBHOOK_SECRET'):raise HTTPException(503,'Payment provider is not configured')
    if not key.startswith('rzp_test_'):raise HTTPException(503,'This MVP supports Razorpay test mode only; live charges are disabled')
    requested_amount=body.amount_paise;discount=0
    def deal_quote():
        from .main import eligibility
        campaign=db.get(Campaign,body.campaign_id)
        if not campaign or campaign.restaurant_id!=restaurant.id:raise HTTPException(422,'Offer does not belong to this restaurant')
        check=eligibility(db,user,campaign)
        if not check['eligible']:raise HTTPException(403,'; '.join(check['reasons']))
        if body.amount_paise<campaign.min_order_paise:raise HTTPException(422,'Minimum order value not reached')
        limits=check['policy_limits']
        benefit=limits['flat_discount_paise'] if limits and limits['flat_discount_paise'] else body.amount_paise*campaign.percent//100
        value=min(benefit,campaign.max_discount_paise,body.amount_paise)
        if limits and value>limits['remaining_paise']:raise HTTPException(409,'Restaurant daily discount budget cannot cover this offer')
        return campaign,check,value
    if body.campaign_id:
        _,_,discount=deal_quote();requested_amount=body.amount_paise-discount
        if requested_amount<100:raise HTTPException(422,'Discounted test payment must be at least ₹1')
    db.commit()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response=await client.post('https://api.razorpay.com/v1/orders',auth=(key,secret),
                json={'amount':requested_amount,'currency':'INR','receipt':uuid.uuid4().hex})
            response.raise_for_status();data=response.json()
        identifier=data['id']
        if not isinstance(identifier,str) or not re.fullmatch(r'order_[A-Za-z0-9]{1,80}',identifier) or type(data['amount']) is not int or data['amount']!=requested_amount or data['currency']!='INR':raise ValueError()
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        raise HTTPException(502,'Payment provider could not create a validated order')
    user=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if not user or not user.consent:raise HTTPException(409,'Consent changed during checkout; no usable order was issued')
    if body.campaign_id:db.scalar(select(Restaurant).where(Restaurant.id==restaurant.id).with_for_update())
    order=PaymentOrder(provider_order_id=identifier,user_id=user.id,restaurant_id=restaurant.id,amount_paise=requested_amount,test_mode=True)
    db.add(order);db.flush()
    if body.campaign_id:
        # All reservations for a restaurant serialize on this row, across different campaigns/users.
        campaign,check,current_discount=deal_quote()
        if current_discount!=discount:raise HTTPException(409,'Offer changed during checkout; please retry')
        reservation=Redemption(user_id=user.id,campaign_id=campaign.id,sequence=(db.scalar(select(func.max(Redemption.sequence)).where(Redemption.user_id==user.id,Redemption.campaign_id==campaign.id)) or 0)+1,order_paise=body.amount_paise,discount_paise=discount,audit=json.dumps({'kind':'pending_test_voucher','eligibility':check}));db.add(reservation);db.flush()
        from datetime import datetime,timedelta,timezone
        db.add(DealVoucher(id=uuid.uuid4().hex,payment_order_id=order.id,redemption_id=reservation.id,expires_at=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()))
    db.commit()
    return {'order_id':identifier,'key_id':key,'amount_paise':requested_amount,'currency':'INR','test_mode':True,'discount_paise':discount,
            'notice':'Use the provider hosted checkout. Only a signed payment.captured webhook verifies spending. No UPI PIN, password or OTP is handled by BiteAI.'}

@router.post('/webhook')
async def captured(request:Request,db=Depends(db_session)):
    secret=os.getenv('RAZORPAY_WEBHOOK_SECRET')
    if not secret:raise HTTPException(501,'Live payment webhook is not configured')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>65536:raise HTTPException(413,'Webhook too large')
    signature=request.headers.get('x-razorpay-signature','')
    expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature):raise HTTPException(401,'Invalid webhook signature')
    try:payload=json.loads(raw)
    except ValueError:raise HTTPException(400,'Invalid JSON')
    if not isinstance(payload,dict):raise HTTPException(400,'Invalid event')
    if payload.get('event') in ('refund.processed','payment.dispute.created','payment.dispute.won','payment.dispute.lost'):
        return adjust_payment(payload,db)
    if payload.get('event')!='payment.captured':return {'status':'ignored'}
    try:
        entity=payload['payload']['payment']['entity']
        payment_id=entity['id'];order_id=entity['order_id'];amount=entity['amount']
        if not isinstance(payment_id,str) or not re.fullmatch(r'pay_[A-Za-z0-9]{1,80}',payment_id):raise ValueError()
        if not isinstance(order_id,str) or not re.fullmatch(r'order_[A-Za-z0-9]{1,80}',order_id):raise ValueError()
        if not isinstance(amount,int) or isinstance(amount,bool) or entity['currency']!='INR' or entity['status']!='captured':raise ValueError()
    except (ValueError,TypeError,KeyError):raise HTTPException(400,'Invalid capture event')
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.provider_order_id==order_id).with_for_update())
    if not order:raise HTTPException(409,'Unknown provider order; manual reconciliation required')
    if order.state=='cancelled':raise HTTPException(409,'Cancelled checkout; provider reconciliation required')
    pending_voucher=db.scalar(select(DealVoucher).where(DealVoucher.payment_order_id==order.id))
    from .database import now
    if pending_voucher and pending_voucher.state=='pending' and pending_voucher.expires_at<=now():raise HTTPException(409,'Voucher reservation expired; provider reconciliation required')
    if amount!=order.amount_paise:raise HTTPException(409,'Amount mismatch')
    reference='razorpay:'+payment_id
    existing=db.scalar(select(Transaction).where(Transaction.reference==reference))
    if existing and (existing.user_id!=order.user_id or existing.restaurant_id!=order.restaurant_id or existing.amount_paise!=amount):
        raise HTTPException(409,'Payment reference conflict; reconciliation required')
    if order.state=='captured':return {'status':'duplicate'}
    if existing:raise HTTPException(409,'Payment reference already assigned; reconciliation required')
    user=db.scalar(select(User).where(User.id==order.user_id).with_for_update().execution_options(populate_existing=True))
    if not user or not user.consent:raise HTTPException(409,'Consent withdrawn; manual provider reconciliation required')
    db.add(Transaction(user_id=order.user_id,restaurant_id=order.restaurant_id,reference=reference,amount_paise=amount,simulated=False,test_mode=order.test_mode,provider_order_id=order.provider_order_id))
    order.state='captured'
    voucher=db.scalar(select(DealVoucher).where(DealVoucher.payment_order_id==order.id))
    if voucher and voucher.state=='pending':
        from datetime import datetime,timedelta,timezone
        voucher.state='issued';voucher.expires_at=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()
    try:db.commit()
    except IntegrityError:
        db.rollback();return {'status':'duplicate'}
    return {'status':'verified','amount_paise':amount}


@router.get('/orders/{order_id}')
def order_status(order_id:str,user=Depends(current_user),db=Depends(db_session)):
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.provider_order_id==order_id,PaymentOrder.user_id==user.id))
    if not order:raise HTTPException(404,'Order not found')
    return {'order_id':order.provider_order_id,'state':order.state,'amount_paise':order.amount_paise,'restaurant_id':order.restaurant_id,'test_mode':order.test_mode,
            'notice':'Only a signed captured webhook credits verified spending.'}


@router.get('/availability/{rid}')
def availability(rid:int,db=Depends(db_session)):
    restaurant=db.get(Restaurant,rid)
    approved={v.strip() for v in os.getenv('RAZORPAY_RESTAURANT_IDS','').split(',')}
    configured=all(os.getenv(key) for key in ('RAZORPAY_KEY_ID','RAZORPAY_KEY_SECRET','RAZORPAY_WEBHOOK_SECRET'))
    return {'test_mode':True,'enabled':bool(configured and os.getenv('RAZORPAY_KEY_ID','').startswith('rzp_test_') and restaurant and not restaurant.sample and str(rid) in approved and (os.getenv('APP_ENV')!='production' or restaurant.ownership_verified))}



def adjust_payment(payload,db):
    event=payload['event'];refund=event=='refund.processed'
    try:
        entity=payload['payload']['refund' if refund else 'dispute']['entity']
        identifier=entity['id'];payment_id=entity['payment_id'];amount=entity['amount']
        if not isinstance(identifier,str) or not re.fullmatch((r'rfnd_' if refund else r'disp_')+r'[A-Za-z0-9]{1,80}',identifier):raise ValueError()
        if not isinstance(payment_id,str) or not re.fullmatch(r'pay_[A-Za-z0-9]{1,80}',payment_id):raise ValueError()
        if type(amount) is not int or amount<=0 or entity.get('currency')!='INR':raise ValueError()
        timestamp=payload.get('created_at',0)
        if not refund and (type(timestamp) is not int or timestamp<=0):raise ValueError()
    except (KeyError,TypeError,ValueError):raise HTTPException(400,'Invalid payment adjustment') from None
    existing=db.scalar(select(Transaction).where(Transaction.reference=='razorpay:'+payment_id,Transaction.simulated.is_(False)))
    if existing and existing.provider_order_id:db.scalar(select(PaymentOrder).where(PaymentOrder.provider_order_id==existing.provider_order_id).with_for_update())
    transaction=db.scalar(select(Transaction).where(Transaction.reference=='razorpay:'+payment_id,Transaction.simulated.is_(False)).with_for_update().execution_options(populate_existing=True))
    if not transaction:raise HTTPException(409,'Unknown payment; provider reconciliation required')
    reference=('refund:'+identifier) if refund else ('dispute:'+identifier+':'+event+':'+str(timestamp))
    previous=db.scalar(select(PaymentAdjustment).where(PaymentAdjustment.reference==reference))
    if previous:
        if previous.transaction_id!=transaction.id or previous.amount_paise!=amount:raise HTTPException(409,'Adjustment reference conflict')
        return {'status':'duplicate'}
    if amount>transaction.amount_paise:raise HTTPException(409,'Adjustment exceeds original payment')
    if refund:
        if transaction.refunded_paise+amount>transaction.amount_paise:raise HTTPException(409,'Cumulative refund exceeds original payment')
        transaction.refunded_paise+=amount
    elif timestamp>transaction.dispute_updated_at:
        transaction.disputed=event!='payment.dispute.won';transaction.dispute_updated_at=timestamp
    if transaction.provider_order_id and (refund or transaction.disputed):
        voucher=db.scalar(select(DealVoucher).join(PaymentOrder).where(PaymentOrder.provider_order_id==transaction.provider_order_id))
        if voucher:voucher.state='revoked'
    db.add(PaymentAdjustment(transaction_id=transaction.id,reference=reference,kind=event,amount_paise=amount));db.commit()
    return {'status':'adjusted','refunded_paise':transaction.refunded_paise,'disputed':transaction.disputed}


@router.post('/orders/{order_id}/cancel')
def cancel_order(order_id:str,user=Depends(current_user),db=Depends(db_session)):
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.provider_order_id==order_id,PaymentOrder.user_id==user.id).with_for_update())
    if not order:raise HTTPException(404,'Order not found')
    if order.state!='created':raise HTTPException(409,'Only an unpaid checkout can be cancelled')
    order.state='cancelled'
    voucher=db.scalar(select(DealVoucher).where(DealVoucher.payment_order_id==order.id))
    if voucher:voucher.state='cancelled'
    db.commit()
    return {'state':'cancelled','notice':'Local unpaid reservation released. Any later provider capture requires reconciliation.'}
