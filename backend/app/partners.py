"""Restaurant profile claims require an independent operator review, never self-attestation."""
import uuid
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Literal
from sqlalchemy import select,func
from .database import Restaurant,RestaurantClaim,Campaign,Search,SearchMatch,User,now
from .security import current_user,owner,verified_user,db_session
from .saarthi import admin
router=APIRouter(tags=['Restaurant partners'])
class Claim(BaseModel):
    restaurant_id:int=Field(ge=1)
    business_reference:str=Field(pattern=r'^(?:[0-9]{14}|[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])$')
@router.post('/partner/claim')
def claim(body:Claim,user=Depends(verified_user),db=Depends(db_session)):
    if user.role!='owner':raise HTTPException(403,'Restaurant owner role required')
    restaurant=db.get(Restaurant,body.restaurant_id)
    if not restaurant or restaurant.sample:raise HTTPException(422,'Choose a real catalogue listing')
    if restaurant.owner_id:raise HTTPException(409,'This listing already has an owner; operator review required')
    from .account_security import throttle
    throttle(db,'partner-claim',str(user.id),limit=5,seconds=3600)
    previous=db.scalar(select(RestaurantClaim).where(RestaurantClaim.user_id==user.id,RestaurantClaim.restaurant_id==restaurant.id,RestaurantClaim.state=='pending'))
    if previous:return {'id':previous.id,'state':previous.state,'notice':'Claim is already awaiting independent review.'}
    row=RestaurantClaim(id=uuid.uuid4().hex,restaurant_id=restaurant.id,user_id=user.id,business_reference=body.business_reference);db.add(row);db.commit()
    return {'id':row.id,'state':row.state,'notice':'Claim submitted for independent business/contact review. Ownership has not been verified.'}
@router.get('/partner/claims')
def claims(user=Depends(owner),db=Depends(db_session)):
    return [{'id':row.id,'restaurant_id':row.restaurant_id,'state':row.state,'review_note':row.review_note} for row in db.scalars(select(RestaurantClaim).where(RestaurantClaim.user_id==user.id).order_by(RestaurantClaim.created_at.desc()).limit(30))]
@router.get('/admin/claims')
def pending(user=Depends(admin),db=Depends(db_session)):
    return [{'id':row.id,'restaurant_id':row.restaurant_id,'user_id':row.user_id,'business_reference':row.business_reference,'state':row.state} for row in db.scalars(select(RestaurantClaim).where(RestaurantClaim.state=='pending').limit(50))]
class Decision(BaseModel):
    decision:Literal['approve','reject']
    note:str=Field(min_length=10,max_length=500)
    business_checked:bool=False
    contact_checked:bool=False
@router.post('/admin/claims/{cid}')
def decide(cid:str,body:Decision,user=Depends(admin),db=Depends(db_session)):
    claim=db.scalar(select(RestaurantClaim).where(RestaurantClaim.id==cid).with_for_update())
    if not claim or claim.state!='pending':raise HTTPException(409,'Claim is no longer pending')
    restaurant=db.scalar(select(Restaurant).where(Restaurant.id==claim.restaurant_id).with_for_update())
    if body.decision=='approve':
        if not body.business_checked or not body.contact_checked:raise HTTPException(422,'Independent business and public-contact checks are required')
        if restaurant.owner_id and restaurant.owner_id!=claim.user_id:raise HTTPException(409,'Listing already belongs to another owner')
        restaurant.owner_id=claim.user_id
    claim.state='approved' if body.decision=='approve' else 'rejected';claim.review_note=body.note;claim.reviewed_by=user.id;db.commit()
    return {'state':claim.state,'notice':'Profile access updated. Website control and merchant payment onboarding remain separate checks.'}
@router.get('/portal/restaurants/{rid}/offer-suggestions')
def suggest(rid:int,user=Depends(owner),db=Depends(db_session)):
    restaurant=db.get(Restaurant,rid)
    if not restaurant or restaurant.owner_id!=user.id:raise HTTPException(403,'You do not own this restaurant')
    cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
    impressions=db.scalar(select(func.count(func.distinct(SearchMatch.search_id))).join(Search,Search.id==SearchMatch.search_id).where(SearchMatch.restaurant_id==rid,Search.created_at>=cutoff)) or 0
    return {'agent':'Saudagar','method':'Deterministic, owner-approved suggestion','impressions_30d':impressions,'suggestions':[{'title':'Reward curious regulars','percent':5,'min_searches':5,'min_order_paise':20000,'max_discount_paise':5000,'daily_budget_paise':50000,'min_tier':'Silver','reason':'A bounded starting offer for engaged users; adjust to your actual margin. It has not been published.'}],'notice':'Suggestions never publish automatically. No demand dip or sales uplift is inferred from insufficient data.'}
