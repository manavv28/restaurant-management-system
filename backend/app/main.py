import json, os, uuid, logging
import threading,time as clock
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, func, delete, or_, and_
from sqlalchemy.exc import IntegrityError
from .database import *
from .security import db_session, current_user, optional_user, owner, passwords, sign_in, COOKIE, verified_user
from .schemas import *
from .agents import AREAS, understand, menu_search, discover_places, clean_places
from .insights import router as insights_router,attribution,resolve_attribution
from .ownership import router as ownership_router
from .platforms import router as platforms_router
from .zomato import router as zomato_router
from .seed import seed
from .account_security import router as security_router
logging.basicConfig(level=logging.INFO)

class PrivateRequestQueries(logging.Filter):
    def filter(self,record):
        # Uvicorn's access record has (address, method, path, version, status).
        # OAuth authorization codes and state must not appear in app access logs.
        if isinstance(record.args,tuple) and len(record.args)==5:
            values=list(record.args)
            if isinstance(values[2],str):
                values[2]=values[2].split('?',1)[0]
                if values[2].startswith(('/research/','/api/research/')):values[2]='/research/[redacted]'
            record.args=tuple(values)
        return True

logging.getLogger('uvicorn.access').addFilter(PrivateRequestQueries())

@asynccontextmanager
async def lifespan(app):
    if os.getenv('APP_ENV')=='production' and is_sqlite:
        raise RuntimeError('Production requires an explicit PostgreSQL DATABASE_URL')
    if os.getenv('AUTO_CREATE_SCHEMA','false' if os.getenv('APP_ENV')=='production' else 'true').lower()=='true':
        Base.metadata.create_all(engine)
    else:
        # Fail startup before accepting traffic if the migration job has not run.
        with Session() as db:
            for table in Base.metadata.sorted_tables: db.execute(select(table).limit(0))
    if os.getenv('SEED_SAMPLE_DATA','false' if os.getenv('APP_ENV')=='production' else 'true').lower() == 'true':
        with Session() as db: seed(db)
    yield

app = FastAPI(title='BiteAI API',version='0.1.0',lifespan=lifespan)
app.include_router(security_router)
app.include_router(insights_router)
app.include_router(ownership_router)
app.include_router(platforms_router)
app.include_router(zomato_router)
from .saarthi import router as concierge_router
app.include_router(concierge_router)
from .vouchers import router as voucher_router
app.include_router(voucher_router)
from .partners import router as partner_router
app.include_router(partner_router)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000,http://127.0.0.1:3000').split(','),allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])

@app.middleware('http')
async def browser_security(request: Request, call_next):
    from starlette.responses import JSONResponse
    if request.method not in ('GET','HEAD','OPTIONS') and request.cookies.get(COOKIE) and not request.headers.get('authorization'):
        # A non-simple header forces a CORS preflight for cross-origin requests.
        # Only same-origin rewrites are supported for browser authentication.
        if request.headers.get('x-biteai-client') != 'browser' or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail':'Browser request verification failed'},status_code=403)
    import time
    started=time.monotonic();request_id=uuid.uuid4().hex
    try:response = await call_next(request)
    except Exception:
        path='/research/[redacted]' if request.url.path.startswith(('/research/','/api/research/')) else request.url.path
        logging.error('request_failed request_id=%s method=%s path=%s',request_id,request.method,path)
        from starlette.responses import JSONResponse
        return JSONResponse({'detail':'Request failed. Please try again.','request_id':request_id},status_code=500)
    response.headers['X-Request-ID']=request_id
    if response.status_code>=500:logging.error('request_error request_id=%s status=%s elapsed_ms=%d',request_id,response.status_code,int((time.monotonic()-started)*1000))
    if request.url.path.startswith(('/auth','/me','/portal','/payments','/platforms','/admin','/partner','/research','/query','/search')):
        response.headers.setdefault('Cache-Control','no-store')
    if request.url.path.startswith('/platforms'):response.headers['Referrer-Policy']='no-referrer'
    return response

@app.post('/auth/logout')
def logout(request:Request,response:Response,user=Depends(current_user),db=Depends(db_session)):
    session=db.get(AuthSession,request.state.session_id)
    if session: db.delete(session); db.commit()
    response.delete_cookie(COOKIE,path='/')
    return {'signed_out':True}

def public(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name not in ('password_hash','source_key')}

def restaurant_or_404(db, rid):
    r = db.get(Restaurant,rid)
    if not r: raise HTTPException(404,'Restaurant not found')
    return r

def owned(db,rid,user):
    r = restaurant_or_404(db,rid)
    if r.owner_id != user.id: raise HTTPException(403,'You do not own this restaurant')
    return r

def stats(db,user_id,restaurant_id=None,days=None):
    searches = db.scalar(select(func.count()).select_from(Search).where(Search.user_id==user_id)) or 0
    tx = select(Transaction).where(Transaction.user_id==user_id,Transaction.simulated.is_(False),Transaction.test_mode.is_(False),Transaction.disputed.is_(False),Transaction.refunded_paise<Transaction.amount_paise)
    if days:tx=tx.where(Transaction.created_at>=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat())
    if restaurant_id: tx = tx.where(Transaction.restaurant_id==restaurant_id)
    transactions = db.scalars(tx).all()
    return {'searches':searches,'verified_spend_paise':sum(t.amount_paise-t.refunded_paise for t in transactions),'verified_visits':len(transactions)}

def eligibility(db,user,campaign):
    state = stats(db,user.id,campaign.restaurant_id,days=30)
    from .saudagar import meaningful_queries,policy_check,active_reservations
    state['searches']=meaningful_queries(db,user.id)
    count = db.scalar(select(func.count()).select_from(Redemption).where(Redemption.user_id==user.id,Redemption.campaign_id==campaign.id,active_reservations())) or 0
    time = now()
    reasons = []
    if not campaign.starts_at <= time <= campaign.ends_at: reasons.append('Campaign is outside its validity period')
    if state['searches'] < campaign.min_searches: reasons.append(f"{campaign.min_searches-state['searches']} more searches needed")
    if state['verified_spend_paise'] < campaign.min_spend_paise: reasons.append('Verified restaurant spending requirement not met')
    if state['verified_visits'] < campaign.min_visits: reasons.append('Verified repeat visits requirement not met')
    if count >= campaign.redemption_limit: reasons.append('Redemption limit reached')
    additional,limits=policy_check(db,user,campaign);reasons.extend(additional)
    return {'eligible':not reasons,'reasons':reasons,'state':state,'redemptions':count,'policy_limits':limits}

@app.get('/health')
def health(db=Depends(db_session)):
    db.execute(select(1))
    return {'release':os.getenv('RENDER_GIT_COMMIT',os.getenv('RELEASE_SHA','development'))[:12],'database_provider':'Supabase' if (database_url.host or '').endswith(('.supabase.co','.pooler.supabase.com')) else engine.dialect.name,'database_tls':database_url.query.get('sslmode','local'),'retention_worker':os.getenv('RETENTION_WORKER_ENABLED','true').lower()=='true','status':'ok','database':'connected','parser':'Gemini' if os.getenv('GEMINI_API_KEY') else 'local model configured' if os.getenv('OLLAMA_URL') else 'local rules','live_platform_comparison':False,'payment_history_access':False,'google_places':bool(os.getenv('GOOGLE_PLACES_API_KEY')),'payments':'provider configured; merchant onboarding required' if all(os.getenv(k) for k in ('RAZORPAY_KEY_ID','RAZORPAY_KEY_SECRET','RAZORPAY_WEBHOOK_SECRET')) else 'provider unavailable', 'payment_simulation':os.getenv('ENABLE_PAYMENT_SIMULATION','true' if os.getenv('APP_ENV')!='production' else 'false').lower()=='true'}

@app.post('/auth/register')
def register(body:Register,request:Request,response:Response,db=Depends(db_session)):
    from .account_security import throttle_auth
    throttle_auth(db,request,body.email)
    user = User(email=body.email.strip().lower(),name=body.name.strip(),password_hash=passwords.hash(body.password),role=body.role)
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,'Email already registered')
    return {**sign_in(user,db,request,response),'user':public(user)}

@app.post('/auth/login')
def login(body:Login,request:Request,response:Response,db=Depends(db_session)):
    from .account_security import throttle_auth
    throttle_auth(db,request,body.email)
    user = db.scalar(select(User).where(User.email==body.email.strip().lower()))
    if not user or not passwords.verify(body.password,user.password_hash): raise HTTPException(401,'Incorrect email or password')
    return {**sign_in(user,db,request,response),'user':public(user)}

@app.get('/me')
def me(user=Depends(current_user),db=Depends(db_session)):
    preference=db.get(Preference,user.id)
    from .saudagar import tier_state
    return {**public(user),**stats(db,user.id),'rewards':tier_state(db,user.id),'preferred_cuisine':preference.preferred_cuisine if preference else ''}

@app.get('/areas')
def areas(): return AREAS

@app.post('/search')
async def search(body:SearchInput,request:Request,user=Depends(optional_user),db=Depends(db_session)):
    from .account_security import throttle
    await run_in_threadpool(throttle,db,'concierge-query',str(user.id) if user else (request.client.host if request.client else 'unknown'),limit=60 if user else 300,seconds=600)
    if body.stream:
        from .saarthi import stream_search
        return await stream_search(body,user.id if user else None)
    await run_in_threadpool(db.commit)
    try:
        intent, parser = await understand(body.query,body.budget,body.radius_km)
        from .saarthi import continued_intent
        intent=continued_intent(body.query,intent,body.context)
    except ValueError:
        raise HTTPException(422,'Budget must be ₹1–100,000 and radius must be greater than zero and at most 50 km')
    data=await run_in_threadpool(search_database,body,intent,parser,user,db)
    await run_in_threadpool(db.commit)
    external=[]
    if not data.get('results') and (intent.location or body.area) in AREAS and os.getenv('GOOGLE_PLACES_API_KEY') and os.getenv('DISCOVERY_ON_MISS','false').lower()=='true':
        try:
            places=await discover_places(intent.location or body.area)
            from .agents import distance_km
            for place in places:
                location=place.get('location',{})
                if 'latitude' not in location or 'longitude' not in location:continue
                distance=distance_km(*( (body.latitude,body.longitude) if body.latitude is not None else AREAS[intent.location or body.area]),location['latitude'],location['longitude'])
                if distance<=intent.radius_km:external.append({'name':place.get('displayName',{}).get('text','Unnamed restaurant'),'address':place.get('formattedAddress',''),'distance_km':round(distance,2),'maps_url':place.get('googleMapsUri',''),'notice':'Google Places discovery only; dish availability and menu prices are unknown.'})
        except Exception:
            logging.warning('External discovery unavailable; returning database results only')
    data['external_discovery']=external
    return data


def search_database(body,intent,parser,user,db,progress=None):
    import time
    started=time.monotonic()
    emit=progress or (lambda name,data:None)
    area = intent.location or body.area
    if area not in AREAS:
        return {'results':[],'follow_up':'Choose an area in Mumbai or share your location.','trace':[]}
    if (body.latitude is None) != (body.longitude is None): raise HTTPException(422,'Supply both latitude and longitude')
    lat,lng = (body.latitude,body.longitude) if body.latitude is not None and not intent.location else AREAS[area]
    trace = [{'agent':'Query understanding','tool':parser,'output':intent.model_dump()},
             {'agent':'Location','tool':'resolve_coordinates','output':{'area':area,'latitude':lat,'longitude':lng,'origin':'gps' if body.latitude is not None and not intent.location else 'area centre','distance_type':'straight-line'}}]
    emit('candidates_found',{'agent':'Khoji','message':'Searching the lake inside your radius','radius_km':intent.radius_km})
    matches = menu_search(db,intent,lat,lng,body.include_samples)
    emit('menu_checked',{'agent':'Munshi','message':'Database menus checked','matched_items':len(matches)})
    preference=db.get(Preference,user.id) if user else None
    if preference and preference.preferred_cuisine and not intent.cuisine and not intent.dish:
        matches.sort(key=lambda row:preference.preferred_cuisine.lower() not in row[0].cuisine.lower())
    # Rank all eligible dishes, then load details once for each restaurant's best match.
    best={}
    for row in matches:best.setdefault(row[0].id,row)
    evidence_by_id={e.menu_item_id:e for e in db.scalars(select(MenuEvidence).where(MenuEvidence.menu_item_id.in_([row[1].id for row in best.values()])))} if best else {}
    from .menu_provenance import source_metadata
    price_sources=source_metadata(db,evidence_by_id)
    campaigns={}
    if user and best:
        for campaign in db.scalars(select(Campaign).where(Campaign.restaurant_id.in_(list(best)))):
            campaigns.setdefault(campaign.restaurant_id,[]).append(campaign)
    unique=[]
    for r,item,distance in best.values():
        offers=[]
        for campaign in campaigns.get(r.id,[]):
            check=eligibility(db,user,campaign)
            if not check['eligible']:continue
            limits=check['policy_limits'];flat=limits['flat_discount_paise'] if limits else 0
            discount=min(flat or item.price_paise*campaign.percent//100,campaign.max_discount_paise,item.price_paise)
            applies=item.price_paise>=campaign.min_order_paise and (not limits or discount<=limits['remaining_paise'])
            offers.append({**public(campaign),'benefit_label':('₹'+str(flat/100)+' off') if flat else str(campaign.percent)+'% off','eligible':True,'discount_paise':discount if applies else 0,'final_price_paise':item.price_paise-discount if applies else item.price_paise,'applies_to_item':applies,'notice':'Offer preview, not a locked-in quote. Checkout and restaurant confirmation required.'})
        dish=menu_details(db,item,evidence_by_id=evidence_by_id,restaurant_row=r,source_metadata_by_id=price_sources)
        note='Fictional sample listing.' if r.sample else 'Price observed on the published menu; confirm with the restaurant.' if item.id in evidence_by_id else 'Owner supplied menu; price not independently verified.'
        if dish.get('price_is_reference'):note='Third-party listed price; confirm the current price and ordering mode with the restaurant.'
        unique.append({'restaurant':public(r),'dish':dish,'distance_km':round(distance,2),'offers':offers,
                       'reason':f"{item.name} is within your ₹{intent.max_budget} budget and {intent.radius_km:g} km radius. "+note})
    trace += [{'agent':'Menu intelligence','tool':'database_price_and_dish_filter','output':{'matched_dishes':len(matches)}},
              {'agent':'Recommendation','tool':'distance_price_rank','output':{'restaurants':len(unique),'preferred_cuisine':preference.preferred_cuisine if preference else None}},
              {'agent':'Discount','tool':'campaign_eligibility','output':{'authenticated':bool(user)}}]
    search_record=Search(user_id=user.id if user else None,query=body.query,cuisine=intent.cuisine,dish=intent.dish,budget=intent.max_budget,area=area,results=len(unique),trace=json.dumps(trace))
    db.add(search_record);db.flush()
    for match in unique:
        db.add(SearchMatch(search_id=search_record.id,restaurant_id=match['restaurant']['id'],menu_item_id=match['dish']['id'],price_paise=match['dish']['price_paise'],distance_km=match['distance_km'],source=match['dish']['source']))
    from .saarthi import verdict,request_research
    emit('price_filtered',{'agent':'Saarthi','matches':len(unique),'budget':intent.max_budget,'message':'Listed prices and distance filters applied'})
    emit('verified',{'agent':'Nigehbaan','message':'Source attribution checked; independent verification is not claimed','source_observations':len(evidence_by_id)})
    emit('offers_applied',{'agent':'Saudagar','message':'Offer eligibility checked','offers':sum(len(r['offers']) for r in unique)})
    data={'external_discovery':[],'attribution':attribution(search_record),'intent':intent,'results':unique,'trace':trace,'parser':parser,'follow_up': ('No matching priced menu was found. Try a larger radius or budget, or another dish.' if body.query and not unique else None) or ('What dish or cuisine are you craving? Try “Hakka noodles under ₹300 within 2 km”.' if body.query and not intent.dish and not intent.cuisine else None),
            'coverage':'Partial Mumbai coverage; source-observed prices require confirmation. Samples are fictional.',
            'nearby_unpriced':unpriced_nearby(db,lat,lng,intent.radius_km) if not unique or not body.stream else [], 'catalog':dict(_coverage_snapshot['data']) if os.getenv('APP_ENV')=='production' and _coverage_snapshot.get('data') else None if os.getenv('APP_ENV')=='production' else catalog_coverage(db)}
    alternatives=[]
    if not unique and (intent.dish or intent.cuisine):
        above=menu_search(db,intent.model_copy(update={'max_budget':100000,'sort':'price'}),lat,lng,body.include_samples)[:3]
        for venue,menu,distance in above:
            if menu.price_paise*(intent.party_size if intent.budget_scope=='total' else 1)<=intent.max_budget*100:continue
            details=menu_details(db,menu,restaurant_row=venue)
            alternatives.append({'restaurant_id':venue.id,'restaurant_name':venue.name,'dish_name':menu.name,'price_paise':menu.price_paise,'listed_subtotal_paise':menu.price_paise*(intent.party_size if intent.budget_scope=='total' else 1),'distance_km':round(distance,2),'price_status':details.get('price_status','Unverified'),'source':menu.source})
    data['alternatives']=alternatives
    data['verdict']=verdict(data,intent)
    data['research']=request_research(db,search_record,data,body,intent) if body.research and body.stream and not unique else {'state':'not_needed' if unique else 'idle','message':'Cached catalogue answer'}
    db.add(AgentRun(id=uuid.uuid4().hex,agent='Saarthi',status='succeeded',search_id=search_record.id,summary=json.dumps({'tools':['parse_intent','geo_menu_search','source_attribution','campaign_eligibility'],'matches':len(unique)}),latency_ms=int((time.monotonic()-started)*1000),cost_microrupees=None if os.getenv('GEMINI_API_KEY') else 0));db.commit()
    return data

@app.post('/query/stream')
async def query_stream(body:SearchInput,request:Request,user=Depends(optional_user),db=Depends(db_session)):
    return await search(body.model_copy(update={'stream':True}),request,user,db)

@app.get('/restaurants/{rid}')
def restaurant(rid:int,db=Depends(db_session)):
    contact_trace=select(IngestionLog.trace).where(IngestionLog.restaurant_id==Restaurant.id,IngestionLog.trace.startswith('{"kind":"public_contact",',autoescape=True)).order_by(IngestionLog.id.desc()).limit(1).correlate(Restaurant).scalar_subquery()
    row=db.execute(select(Restaurant,contact_trace).where(Restaurant.id==rid)).first()
    if not row:raise HTTPException(404,'Restaurant not found')
    r,contact=row
    from .contact_enrichment import public_contact
    restaurant_data=public(r);contact_info=public_contact(r.phone,contact)
    if contact_info:restaurant_data['phone_source']=contact_info
    menu=db.scalars(select(MenuItem).where(MenuItem.restaurant_id==rid)).all()
    evidence={e.menu_item_id:e for e in db.scalars(select(MenuEvidence).where(MenuEvidence.menu_item_id.in_([m.id for m in menu])))} if menu else {}
    from .menu_provenance import source_metadata
    price_sources=source_metadata(db,evidence)
    return {'restaurant':restaurant_data,'menu':[menu_details(db,m,evidence_by_id=evidence,restaurant_row=r,source_metadata_by_id=price_sources) for m in menu]}

@app.post('/restaurants/{rid}/click')
def click(rid:int,body:ClickInput|None=None,user=Depends(optional_user),db=Depends(db_session)):
    restaurant_or_404(db,rid)
    sid=resolve_attribution(db,body.attribution,rid,user) if body and body.attribution else None
    if sid and db.scalar(select(Interaction.id).where(Interaction.search_id==sid,Interaction.restaurant_id==rid)):return {'recorded':True}
    db.add(Interaction(restaurant_id=rid,search_id=sid))
    try:db.commit()
    except IntegrityError:db.rollback()
    return {'recorded':True}

@app.get('/me/history')
def history(user=Depends(current_user),db=Depends(db_session)):
    return [public(s) for s in db.scalars(select(Search).where(Search.user_id==user.id).order_by(Search.id.desc()).limit(50)).all()]

@app.delete('/me/history')
def clear_history(user=Depends(current_user),db=Depends(db_session)):
    db.execute(delete(Search).where(Search.user_id==user.id)); db.commit()
    return {'deleted':True}

@app.get('/me/favourites')
def favourites(user=Depends(current_user),db=Depends(db_session)):
    rows = db.scalars(select(Favourite).where(Favourite.user_id==user.id)).all()
    restaurants={r.id:r for r in db.scalars(select(Restaurant).where(Restaurant.id.in_({f.restaurant_id for f in rows})))} if rows else {}
    items={m.id:m for m in db.scalars(select(MenuItem).where(MenuItem.id.in_({f.menu_item_id for f in rows if f.menu_item_id})))} if rows else {}
    evidence={e.menu_item_id:e for e in db.scalars(select(MenuEvidence).where(MenuEvidence.menu_item_id.in_(list(items))))} if items else {}
    from .menu_provenance import source_metadata
    metadata=source_metadata(db,evidence)
    return [{**public(f),'restaurant':public(restaurants[f.restaurant_id]),'dish':menu_details(db,items[f.menu_item_id],evidence_by_id=evidence,restaurant_row=restaurants[f.restaurant_id],source_metadata_by_id=metadata) if f.menu_item_id in items else None} for f in rows]

@app.post('/me/favourites/{rid}')
def favourite(rid:int,menu_item_id:int=0,user=Depends(current_user),db=Depends(db_session)):
    restaurant_or_404(db,rid)
    if menu_item_id:
        item = db.get(MenuItem,menu_item_id)
        if not item or item.restaurant_id != rid: raise HTTPException(404,'Dish not found')
    f = db.scalar(select(Favourite).where(Favourite.user_id==user.id,Favourite.restaurant_id==rid,Favourite.menu_item_id==menu_item_id))
    if f: db.delete(f)
    else: db.add(Favourite(user_id=user.id,restaurant_id=rid,menu_item_id=menu_item_id))
    db.commit(); return {'saved':f is None}

@app.put('/me/consent')
def consent(body:ConsentInput,user=Depends(current_user),db=Depends(db_session)):
    user=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    user.consent=body.consent; db.commit()
    return {'consent':user.consent,'scope':'BiteAI payment records only; no GPay/UPI account history access','retention_days':365,'message':'Withdrawal stops new consent-gated payment processing. Existing payment audit records are retained for up to 365 days; query-based rewards remain available.'}

@app.get('/me/transactions')
def transactions(user=Depends(current_user),db=Depends(db_session)):
    return [public(t) for t in db.scalars(select(Transaction).where(Transaction.user_id==user.id).order_by(Transaction.id.desc()).limit(100)).all()]

@app.post('/payments/simulate')
def simulate(body:TransactionInput,user=Depends(current_user),db=Depends(db_session)):
    if os.getenv('ENABLE_PAYMENT_SIMULATION','false' if os.getenv('APP_ENV')=='production' else 'true').lower() != 'true': raise HTTPException(403,'Simulation disabled')
    if not user.consent: raise HTTPException(403,'Explicit payment-data consent required')
    restaurant_or_404(db,body.restaurant_id)
    t = Transaction(user_id=user.id,restaurant_id=body.restaurant_id,reference='SIM-'+uuid.uuid4().hex,amount_paise=body.amount_paise,simulated=True)
    db.add(t); db.commit()
    return {**public(t),'notice':'Simulated only. Does not count toward verified spending or repeat visits.'}

from .payments import router as payments_router
app.include_router(payments_router)

@app.get('/me/offers')
def offers(user=Depends(current_user),db=Depends(db_session)):
    return [{**public(c),'benefit_label':('₹'+str(policy.flat_discount_paise/100)+' off') if (policy:=db.get(CampaignPolicy,c.id)) and policy.flat_discount_paise else str(c.percent)+'% off','restaurant_name':db.get(Restaurant,c.restaurant_id).name,**eligibility(db,user,c)} for c in db.scalars(select(Campaign)).all()]

@app.get('/me/redemptions')
def redemptions(user=Depends(current_user),db=Depends(db_session)):
    return [public(r) for r in db.scalars(select(Redemption).where(Redemption.user_id==user.id)).all()]

@app.post('/campaigns/{cid}/redeem')
def redeem(cid:int,body:RedeemInput,user=Depends(verified_user),db=Depends(db_session)):
    # Serialize each user's redemptions on PostgreSQL; unique sequence protects SQLite races.
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    c = db.get(Campaign,cid)
    if c:db.scalar(select(Restaurant).where(Restaurant.id==c.restaurant_id).with_for_update())
    if not c: raise HTTPException(404,'Campaign not found')
    check=eligibility(db,user,c)
    if not check['eligible']: raise HTTPException(403,check['reasons'])
    if body.order_paise < c.min_order_paise: raise HTTPException(422,'Minimum order value not reached')
    limits=check.get('policy_limits')
    discount=min((limits['flat_discount_paise'] if limits and limits['flat_discount_paise'] else body.order_paise*c.percent//100),c.max_discount_paise,body.order_paise)
    if limits and discount>limits['remaining_paise']:raise HTTPException(409,'Restaurant daily discount budget cannot cover this offer')
    r=Redemption(user_id=user.id,campaign_id=cid,sequence=(db.scalar(select(func.max(Redemption.sequence)).where(Redemption.user_id==user.id,Redemption.campaign_id==cid)) or 0)+1,order_paise=body.order_paise,discount_paise=discount,audit=json.dumps({'eligibility':check,'campaign':public(c),'calculation':'min(order_paise * percent // 100, cap)'}))
    db.add(r)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,'Concurrent redemption; retry')
    return {**public(r),'notice':'Records an offer reservation, not a payment or proof of purchase.'}

@app.get('/portal/restaurants')
def my_restaurants(user=Depends(owner),db=Depends(db_session)):
    return [public(r) for r in db.scalars(select(Restaurant).where(Restaurant.owner_id==user.id)).all()]

@app.post('/portal/restaurants')
def create_restaurant(body:RestaurantInput,user=Depends(owner),db=Depends(db_session)):
    r=Restaurant(**body.model_dump(),owner_id=user.id)
    db.add(r); db.commit(); return public(r)

@app.put('/portal/restaurants/{rid}')
def update_restaurant(rid:int,body:RestaurantInput,user=Depends(owner),db=Depends(db_session)):
    r=owned(db,rid,user)
    for k,v in body.model_dump().items(): setattr(r,k,v)
    from urllib.parse import urlsplit
    proof=db.get(OwnershipProof,rid)
    if proof and urlsplit(r.website).hostname!=proof.hostname:
        r.ownership_verified=False;db.delete(proof)
    r.updated_at=now(); db.commit(); return public(r)

@app.post('/portal/restaurants/{rid}/menu')
def add_menu(rid:int,body:MenuInput,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    m=MenuItem(restaurant_id=rid,**body.model_dump()); db.add(m); db.commit(); return public(m)

@app.put('/portal/restaurants/{rid}/menu/{mid}')
def update_menu(rid:int,mid:int,body:MenuInput,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    m=db.get(MenuItem,mid)
    if not m or m.restaurant_id != rid: raise HTTPException(404,'Menu item not found')
    for k,v in body.model_dump().items(): setattr(m,k,v)
    m.verified_at=None;m.source_key=None;m.source='Owner supplied; unverified'
    evidence=db.get(MenuEvidence,m.id)
    if evidence:db.delete(evidence)
    db.commit(); return public(m)

@app.post('/portal/restaurants/{rid}/campaigns')
def campaign(rid:int,body:CampaignInput,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    if not body.starts_at.tzinfo or not body.ends_at.tzinfo or body.ends_at <= body.starts_at: raise HTTPException(422,'Supply timezone-aware, ordered campaign dates')
    values=body.model_dump(exclude={'min_tier','cuisine','cuisine_queries_30d','daily_budget_paise','flat_discount_paise'})
    values.update(starts_at=body.starts_at.astimezone(timezone.utc).isoformat(),ends_at=body.ends_at.astimezone(timezone.utc).isoformat())
    c=Campaign(restaurant_id=rid,**values); db.add(c);db.flush()
    policy=CampaignPolicy(campaign_id=c.id,**body.model_dump(include={'min_tier','cuisine','cuisine_queries_30d','daily_budget_paise','flat_discount_paise'}));db.add(policy);db.commit();return {**public(c),'policy':public(policy)}

@app.get('/portal/restaurants/{rid}/analytics')
def analytics(rid:int,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    clicks=db.scalar(select(func.count()).select_from(Interaction).where(Interaction.restaurant_id==rid))
    campaigns=db.scalars(select(Campaign).where(Campaign.restaurant_id==rid)).all()
    ids=[c.id for c in campaigns]
    redeemed=db.scalars(select(Redemption).where(Redemption.campaign_id.in_(ids))).all()
    # Restaurant portal receives only aggregate engagement, never individual searches.
    return {'restaurant_clicks':clicks,'campaigns':[public(c) for c in campaigns],'redemptions':len(redeemed),'discount_paise':sum(r.discount_paise for r in redeemed)}

@app.get('/analytics')
def aggregate(db=Depends(db_session)):
    count=db.scalar(select(func.count()).select_from(Search)) or 0
    clicks=db.scalar(select(func.count()).select_from(Interaction)) or 0
    def group(column):
        return [{'label':label or 'Unspecified','count':n} for label,n in db.execute(select(column,func.count()).group_by(column).order_by(func.count().desc()).limit(8)).all()]
    return {'searches':count,'restaurant_clicks':clicks,'average_budget':round(db.scalar(select(func.avg(Search.budget))) or 0),
            'cuisines':group(Search.cuisine),'dishes':group(Search.dish),'areas':group(Search.area),
            'note':'Aggregate clicks and searches are independent counts, not attributed conversions.'}

@app.post('/portal/discover/{area}')
async def discover(area:str,user=Depends(owner),db=Depends(db_session)):
    if area not in AREAS: raise HTTPException(422,'Choose a supported Mumbai area')
    try:
        places=await discover_places(area)
        return {'places':places,'data_lake':clean_places(db,places,area),'source':'Google Maps / Places','notice':'Live provider metadata. No menus or prices inferred. Do not retain beyond provider terms.'}
    except ValueError as exc: raise HTTPException(503,str(exc))
    except Exception:
        logging.exception('Places discovery failed')
        raise HTTPException(502,'Google Places unavailable; no data was imported')

@app.post('/portal/restaurants/{rid}/ingest')
def ingest(rid:int,body:IngestionInput,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    if not body.permission_confirmed: raise HTTPException(422,'Confirm permission to use this menu source')
    changes=[]
    for incoming in body.items:
        normalized=' '.join(incoming.name.split())
        existing=db.scalar(select(MenuItem).where(MenuItem.restaurant_id==rid,func.lower(MenuItem.name)==normalized.lower()))
        before=existing.price_paise if existing else None
        if existing:
            evidence=db.get(MenuEvidence,existing.id)
            if evidence:db.delete(evidence)
            for key,value in incoming.model_dump().items():setattr(existing,key,value)
            existing.name=normalized;existing.source=body.source+' (owner supplied; unverified)';existing.verified_at=None
        else:
            db.add(MenuItem(restaurant_id=rid,**{**incoming.model_dump(),'name':normalized},source=body.source+' (owner supplied; unverified)'))
        changes.append({'dish':normalized,'previous_price_paise':before,'price_paise':incoming.price_paise})
        db.flush()
    trace=[{'agent':'Menu intelligence','tool':'validate_and_normalize_menu','items':len(changes)},
           {'agent':'Data lake','tool':'deduplicate_and_upsert','changes':changes}]
    log=IngestionLog(restaurant_id=rid,source=body.source,trace=json.dumps(trace))
    db.add(log);db.commit()
    return {'trace':trace,'ingestion_id':log.id,'notice':'Owner supplied data. Prices are not independently verified.'}

@app.get('/portal/restaurants/{rid}/ingestions')
def ingestion_history(rid:int,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    return [public(row) for row in db.scalars(select(IngestionLog).where(IngestionLog.restaurant_id==rid).order_by(IngestionLog.id.desc()).limit(50)).all()]

@app.put('/me/profile')
def profile(body:ProfileInput,user=Depends(current_user),db=Depends(db_session)):
    user.name=body.name.strip()
    if not user.name: raise HTTPException(422,'Name cannot be blank')
    preference=db.get(Preference,user.id)
    if not preference: preference=Preference(user_id=user.id);db.add(preference)
    preference.preferred_cuisine=body.preferred_cuisine
    db.commit()
    return {**public(user),'preferred_cuisine':preference.preferred_cuisine}

_coverage_snapshot={}
_coverage_lock=threading.Lock()

@app.get('/catalog/coverage')
def catalog_coverage(db=Depends(db_session)):
    if os.getenv('APP_ENV')!='production':return calculate_coverage(db)
    if _coverage_snapshot.get('data') and clock.monotonic()-_coverage_snapshot['stored_at']<60:return dict(_coverage_snapshot['data'])
    with _coverage_lock:
        if _coverage_snapshot.get('data') and clock.monotonic()-_coverage_snapshot['stored_at']<60:return dict(_coverage_snapshot['data'])
        data=calculate_coverage(db);_coverage_snapshot.update(data=data,stored_at=clock.monotonic());return dict(data)

def calculate_coverage(db):
    snapshot_at=now()
    real_counts=select(func.count().filter(Restaurant.sample.is_(False)).label('real_restaurants'),func.count().filter(Restaurant.sample.is_(True)).label('sample_restaurants'),func.count().filter(Restaurant.sample.is_(False),Restaurant.phone!='').label('public_phone_restaurants')).subquery()
    price_counts=select(func.count(MenuEvidence.menu_item_id).label('fresh_source_menu_items'),func.count(func.distinct(MenuItem.restaurant_id)).label('source_priced_restaurants')).select_from(MenuEvidence).join(MenuItem,MenuItem.id==MenuEvidence.menu_item_id).join(Restaurant,Restaurant.id==MenuItem.restaurant_id).where(MenuItem.available.is_(True),Restaurant.sample.is_(False),MenuEvidence.active.is_(True),MenuEvidence.expires_at>now()).subquery()
    source_counts=select(func.count().filter(CatalogSource.enabled.is_(True)).label('enabled_sources'),func.max(CatalogSource.checked_at).label('last_source')).subquery()
    statement=select(real_counts,price_counts,source_counts,select(func.max(CatalogIdentity.observed_at)).scalar_subquery().label('last_identity')).select_from(real_counts.join(price_counts,text('true')).join(source_counts,text('true')))
    counts=dict(db.execute(statement).mappings().one())
    last=max((value for value in (counts.pop('last_source'),counts.pop('last_identity')) if value),default=None)
    return {**counts,'menu_coverage_percent':round(100*counts['source_priced_restaurants']/counts['real_restaurants'],1) if counts['real_restaurants'] else 0,'unpriced_restaurants':max(0,counts['real_restaurants']-counts['source_priced_restaurants']),'snapshot_at':snapshot_at,'cache_max_age_seconds':60 if os.getenv('APP_ENV')=='production' else 0,'phone_coverage_percent':round(100*counts['public_phone_restaurants']/counts['real_restaurants'],1) if counts['real_restaurants'] else 0,'last_successful_collection':last,
            'coverage':'Mumbai City and Mumbai Suburban listings; coverage is not exhaustive. Prices are published observations, not real-time restaurant quotes. Third-party listings may be dated and differ for delivery, portions or fees; source dates are shown where available.',
            'attribution':'Menu listing facts when present: IndiaRestros and its named sources (public API terms). Place sources: Overture Maps contributors (CDLA Permissive 2.0, Apache 2.0, CC0); © OpenStreetMap contributors (ODbL). See data sources for notices.'}

@app.post('/portal/restaurants/{rid}/sources')
def add_source(rid:int,body:MenuSourceInput,user=Depends(owner),db=Depends(db_session)):
    from .catalog import approved_url
    r=owned(db,rid,user)
    if r.sample:raise HTTPException(422,'Cannot attach real sources to fictional samples')
    try:approved_url(body.url)
    except ValueError as exc:raise HTTPException(422,str(exc))
    if db.scalar(select(CatalogSource.id).where(CatalogSource.url==body.url,CatalogSource.restaurant_id==rid)):
        raise HTTPException(409,'Source already registered')
    source=CatalogSource(kind='approved_menu',url=body.url,restaurant_id=rid,area=r.area,permission_note=body.permission_note,refresh_hours=body.refresh_hours)
    db.add(source);db.flush();db.add(CatalogJob(source_id=source.id));db.commit()
    return {'source_id':source.id,'state':'queued','message':'A separate worker collects this source; registration does not mean it was fetched.'}

@app.get('/portal/restaurants/{rid}/sources')
def source_jobs(rid:int,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    sources=db.scalars(select(CatalogSource).where(CatalogSource.restaurant_id==rid)).all()
    return [{**public(s),'jobs':[public(j) for j in db.scalars(select(CatalogJob).where(CatalogJob.source_id==s.id).order_by(CatalogJob.id.desc()).limit(10))]} for s in sources]

def unpriced_nearby(db,lat,lng,radius):
    from .agents import distance_km
    from .geo import candidates
    fresh_item=select(MenuItem.id).outerjoin(MenuEvidence,MenuEvidence.menu_item_id==MenuItem.id).where(
        MenuItem.restaurant_id==Restaurant.id,MenuItem.available.is_(True),
        or_(MenuEvidence.menu_item_id.is_(None),and_(MenuEvidence.active.is_(True),MenuEvidence.expires_at>now()))).exists()
    query=select(Restaurant).where(Restaurant.sample.is_(False),~fresh_item)
    rows=db.scalars(candidates(db,query,lat,lng,radius)).all()
    output=[]
    for restaurant in rows:
        distance=distance_km(lat,lng,restaurant.latitude,restaurant.longitude)
        if distance<=radius:output.append({'restaurant':public(restaurant),'distance_km':round(distance,2),'notice':'Menu price unavailable or stale. This is not a confirmed dish/budget match.'})
    return sorted(output,key=lambda row:row['distance_km'])[:20]

def menu_details(db,item,*,evidence_by_id=None,restaurant_row=None,source_metadata_by_id=None):
    evidence=evidence_by_id.get(item.id) if evidence_by_id is not None else db.get(MenuEvidence,item.id)
    if evidence:
        from .menu_provenance import evidence_metadata
        return {**public(item),**evidence_metadata(evidence,source_metadata_by_id)}
    return {**public(item),'price_status':'sample' if (restaurant_row if restaurant_row is not None else db.get(Restaurant,item.restaurant_id)).sample else 'owner supplied; unverified','source_expires_at':None}



@app.put('/portal/restaurants/{rid}/sources/{sid}')
def source_enabled(rid:int,sid:int,body:SourceState,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    source=db.scalar(select(CatalogSource).where(CatalogSource.id==sid,CatalogSource.restaurant_id==rid).with_for_update())
    if not source:raise HTTPException(404,'Source not found')
    source.enabled=body.enabled
    if not body.enabled:
        for evidence in db.scalars(select(MenuEvidence).where(MenuEvidence.source_id==sid)): evidence.active=False
    db.commit()
    return {'source_id':sid,'enabled':source.enabled,'message':'Source enabled; prices refresh after successful collection.' if body.enabled else 'Collection disabled and source prices withdrawn.'}

@app.post('/portal/restaurants/{rid}/sources/{sid}/refresh')
def refresh_source(rid:int,sid:int,user=Depends(owner),db=Depends(db_session)):
    owned(db,rid,user)
    source=db.get(CatalogSource,sid)
    if not source or source.restaurant_id!=rid:raise HTTPException(404,'Source not found')
    if not source.enabled:raise HTTPException(409,'Enable the source before refreshing')
    existing=db.scalar(select(CatalogJob).where(CatalogJob.source_id==sid,CatalogJob.state.in_(['queued','running'])))
    if existing:return {'job_id':existing.id,'state':existing.state}
    job=CatalogJob(source_id=sid);db.add(job)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'Refresh already queued; reload status')
    return {'job_id':job.id,'state':job.state}

@app.get('/catalog/restaurants')
def catalog_directory(q:str='',area:str='',after:int=0,limit:int=20,db=Depends(db_session)):
    if len(q)>150 or limit<1 or limit>50 or after<0:
        raise HTTPException(422,'Use a name up to 150 characters and a page size from 1 to 50')
    if area and area not in AREAS: raise HTTPException(422,'Choose a supported Mumbai area')
    statement=select(Restaurant).where(Restaurant.sample.is_(False),Restaurant.id>after)
    if q.strip(): statement=statement.where(Restaurant.name.icontains(q.strip(),autoescape=True))
    if area: statement=statement.where(Restaurant.area==area)
    rows=db.scalars(statement.order_by(Restaurant.id).limit(limit+1)).all()
    return {'restaurants':[public(r) for r in rows[:limit]],
            'next_cursor':rows[limit-1].id if len(rows)>limit else None,
            'notice':'Listings are source supplied and may be outdated. Menus and prices are shown only when separately available.'}
