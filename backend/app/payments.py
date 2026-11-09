"""Optional Razorpay orders and signed capture webhooks. No GPay history access."""
import hashlib
import hmac
import json
import os
import re
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .database import PaymentOrder, Restaurant, Transaction, User
from .schemas import TransactionInput
from .security import current_user, db_session

router=APIRouter(prefix='/payments',tags=['Verified payments'])

@router.post('/orders')
async def create_order(body:TransactionInput,user=Depends(current_user),db=Depends(db_session)):
    if not user.consent:raise HTTPException(403,'Payment-data consent is required')
    restaurant=db.get(Restaurant,body.restaurant_id)
    if not restaurant or restaurant.sample:raise HTTPException(422,'A real restaurant is required')
    approved={v.strip() for v in os.getenv('RAZORPAY_RESTAURANT_IDS','').split(',')}
    if str(restaurant.id) not in approved:raise HTTPException(503,'Restaurant payment onboarding is incomplete')
    key,secret=os.getenv('RAZORPAY_KEY_ID'),os.getenv('RAZORPAY_KEY_SECRET')
    if not key or not secret:raise HTTPException(503,'Payment provider is not configured')
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response=await client.post('https://api.razorpay.com/v1/orders',auth=(key,secret),
                json={'amount':body.amount_paise,'currency':'INR','receipt':uuid.uuid4().hex})
            response.raise_for_status();data=response.json()
        identifier=data['id']
        if not re.fullmatch(r'order_[A-Za-z0-9]{1,80}',identifier) or data['amount']!=body.amount_paise or data['currency']!='INR':raise ValueError()
    except (httpx.HTTPError,ValueError,KeyError):
        raise HTTPException(502,'Payment provider could not create a validated order')
    order=PaymentOrder(provider_order_id=identifier,user_id=user.id,restaurant_id=restaurant.id,amount_paise=body.amount_paise)
    db.add(order);db.commit()
    return {'order_id':identifier,'key_id':key,'amount_paise':body.amount_paise,'currency':'INR',
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
    if payload.get('event')!='payment.captured':return {'status':'ignored'}
    try:
        entity=payload['payload']['payment']['entity']
        payment_id=entity['id'];order_id=entity['order_id'];amount=entity['amount']
        if not re.fullmatch(r'pay_[A-Za-z0-9]{1,80}',payment_id):raise ValueError()
        if not isinstance(amount,int) or isinstance(amount,bool) or entity['currency']!='INR' or entity['status']!='captured':raise ValueError()
    except (ValueError,TypeError,KeyError):raise HTTPException(400,'Invalid capture event')
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.provider_order_id==order_id).with_for_update())
    if not order:raise HTTPException(409,'Unknown provider order; manual reconciliation required')
    if amount!=order.amount_paise:raise HTTPException(409,'Amount mismatch')
    reference='razorpay:'+payment_id
    if order.state=='captured' or db.scalar(select(Transaction.id).where(Transaction.reference==reference)):
        return {'status':'duplicate'}
    user=db.get(User,order.user_id)
    if not user or not user.consent:raise HTTPException(409,'Consent withdrawn; manual provider reconciliation required')
    db.add(Transaction(user_id=order.user_id,restaurant_id=order.restaurant_id,reference=reference,amount_paise=amount,simulated=False))
    order.state='captured'
    try:db.commit()
    except IntegrityError:
        db.rollback();return {'status':'duplicate'}
    return {'status':'verified','amount_paise':amount}
