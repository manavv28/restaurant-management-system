"""Aggregate insights and signed attribution; no individual queries in owner reports."""
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func
from .database import *
from .security import SECRET,db_session,current_user,optional_user,owner
from .agents import AREAS,Intent,menu_search
router=APIRouter(tags=['Insights'])

def public(obj):return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name not in ('password_hash','source_key')}

def attribution(search):
    return jwt.encode({'aud':'biteai-click','search_id':search.id,'user_id':search.user_id or 0,'exp':datetime.now(timezone.utc)+timedelta(minutes=30)},SECRET,algorithm='HS256')

def resolve_attribution(db,value,rid,user):
    try:claims=jwt.decode(value,SECRET,algorithms=['HS256'],audience='biteai-click',options={'require':['exp','search_id','user_id']})
    except jwt.PyJWTError:raise HTTPException(400,'Search attribution expired; search again') from None
    if claims['user_id'] and (not user or claims['user_id']!=user.id):raise HTTPException(403,'Search belongs to another account')
    match=db.scalar(select(SearchMatch.id).where(SearchMatch.search_id==claims['search_id'],SearchMatch.restaurant_id==rid))
    if not match:raise HTTPException(400,'Restaurant was not returned by this search')
    return claims['search_id']

def funnel(db,rid=None):
    clicks=select(func.count(func.distinct(Interaction.search_id))).where(Interaction.search_id.is_not(None))
    if rid:
        denominator=db.scalar(select(func.count(func.distinct(SearchMatch.search_id))).where(SearchMatch.restaurant_id==rid)) or 0
        clicks=clicks.where(Interaction.restaurant_id==rid)
    else:denominator=db.scalar(select(func.count()).select_from(Search)) or 0
    numerator=db.scalar(clicks) or 0
    return {'searches_with_results':denominator,'searches_with_click':numerator,'conversion_percent':round(numerator*100/denominator,2) if denominator else 0}

@router.get('/insights')
def insights(db=Depends(db_session)):
    def grouped(column):return [{'label':label or 'Unspecified','count':count} for label,count in db.execute(select(column,func.count()).group_by(column).order_by(func.count().desc()).limit(8))]
    return {'cuisines':grouped(Search.cuisine),'dishes':grouped(Search.dish),'areas':grouped(Search.area),'funnel':funnel(db),
            'average_budget':round(db.scalar(select(func.avg(Search.budget))) or 0)}

@router.get('/popular-dishes')
def popular(include_samples:bool=True,db=Depends(db_session)):
    rows=db.execute(select(MenuItem,Restaurant,func.count(SearchMatch.id)).join(Restaurant,Restaurant.id==MenuItem.restaurant_id).join(SearchMatch,SearchMatch.menu_item_id==MenuItem.id).where(MenuItem.available.is_(True)).group_by(MenuItem.id,Restaurant.id).order_by(func.count(SearchMatch.id).desc(),MenuItem.id).limit(100)).all()
    output=[]
    from .menu_provenance import source_metadata,evidence_metadata
    evidence_by_id={e.menu_item_id:e for e in db.scalars(select(MenuEvidence).where(MenuEvidence.menu_item_id.in_([row[0].id for row in rows])))} if rows else {}
    metadata=source_metadata(db,evidence_by_id)
    for item,restaurant,count in rows:
        evidence=evidence_by_id.get(item.id)
        if restaurant.sample and not include_samples:continue
        if evidence and (not evidence.active or evidence.expires_at<=now()):continue
        output.append({'dish':{**public(item),**(evidence_metadata(evidence,metadata) if evidence else {'price_status':'sample' if restaurant.sample else 'owner supplied; unverified'})},'restaurant':public(restaurant),'appearances':count})
        if len(output)==6:break
    return output

@router.get('/me/recommendations')
def recommendations(area:str='Bandra',include_samples:bool=True,user=Depends(current_user),db=Depends(db_session)):
    if area not in AREAS:raise HTTPException(422,'Choose a supported Mumbai area')
    preference=db.get(Preference,user.id)
    cuisine=preference.preferred_cuisine if preference else None
    matches=menu_search(db,Intent(cuisine=cuisine or None,max_budget=100000,radius_km=10),*AREAS[area],include_samples)
    from .menu_provenance import source_metadata,evidence_metadata
    evidence_by_id={e.menu_item_id:e for e in db.scalars(select(MenuEvidence).where(MenuEvidence.menu_item_id.in_([row[1].id for row in matches])))} if matches else {}
    metadata=source_metadata(db,evidence_by_id)
    seen=set();output=[]
    for restaurant,item,distance in matches:
        if restaurant.id in seen:continue
        seen.add(restaurant.id)
        output.append({'restaurant':public(restaurant),'dish':{**public(item),**(evidence_metadata(evidence_by_id[item.id],metadata) if item.id in evidence_by_id else {'price_status':'sample' if restaurant.sample else 'owner supplied; unverified'})},'distance_km':round(distance,2),'reason':f'{cuisine} matches your saved cuisine preference.' if cuisine else 'Ranked by distance, price and available rating near your selected area.'})
        if len(output)==6:break
    return output

@router.get('/portal/restaurants/{rid}/performance')
def performance(rid:int,user=Depends(owner),db=Depends(db_session)):
    restaurant=db.get(Restaurant,rid)
    if not restaurant:raise HTTPException(404,'Restaurant not found')
    if restaurant.owner_id!=user.id:raise HTTPException(403,'You do not own this restaurant')
    campaigns=db.scalars(select(Campaign).where(Campaign.restaurant_id==rid)).all()
    reports=[]
    for campaign in campaigns:
        count,total,orders=db.execute(select(func.count(Redemption.id),func.coalesce(func.sum(Redemption.discount_paise),0),func.coalesce(func.sum(Redemption.order_paise),0)).where(Redemption.campaign_id==campaign.id)).one()
        reports.append({'id':campaign.id,'title':campaign.title,'reservations':count,'discount_paise':total,'reserved_order_paise':orders,'notice':'Reservations are not verified sales.'})
    return {'funnel':funnel(db,rid),'campaigns':reports,'privacy':'Aggregate impressions and clicks only. Individual queries are never exposed.'}
