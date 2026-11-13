"""Saarthi: validated intent, database-only verdicts, honest confidence and streamed work."""
import asyncio,json,re,time,uuid
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import jwt
from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter,Depends,HTTPException,Request
from starlette.responses import StreamingResponse
from sqlalchemy import select,func,delete
from .database import Session,User,AgentRun,CatalogJob,CatalogSource,ResearchRequest,BronzeArtifact,MenuEvidence,MenuItem,IngestionLog,now
from .security import SECRET,optional_user,current_user,db_session
from .agents import Intent,understand
router=APIRouter(tags=['Concierge'])
RESEARCH_GATE=asyncio.Semaphore(1)

def opening_status(hours,at=None):
    """Only interpret explicit simple hours; never infer an unknown restaurant is open."""
    if hours=='24/7':return {'open':True,'label':'Listed open 24/7; confirm with restaurant'}
    current=(at or datetime.now(timezone.utc)).astimezone(ZoneInfo('Asia/Kolkata'))
    match=re.fullmatch(r'(?:(Mo-Su|Mo-Fr|Sa-Su)\s+)?(\d{2}:\d{2})-(\d{2}:\d{2})',hours or '')
    if not match:return {'open':None,'label':'Opening status unknown'}
    days=match[1]
    if days=='Mo-Fr' and current.weekday()>4 or days=='Sa-Su' and current.weekday()<5:return {'open':False,'label':'Listed closed; confirm with restaurant'}
    try:
        start=datetime.strptime(match[2],'%H:%M').time();end=datetime.strptime(match[3],'%H:%M').time()
    except ValueError:return {'open':None,'label':'Opening status unknown'}
    t=current.time().replace(tzinfo=None)
    opened=start<=t<end if start<end else t>=start or t<end
    return {'open':opened,'label':('Listed open' if opened else 'Listed closed')+'; confirm with restaurant'}

def continued_intent(query,intent,context):
    if not context:return intent
    if not re.search(r'isme|inme|aur sasta|sabse paas|nearest|closest|veg (?:only|wale)|cheaper|same|these',query,re.I):return intent
    previous=Intent.model_validate(context)
    values=intent.model_dump();q=query.casefold()
    for field in ('dish','cuisine','location','diet'):
        if values[field] is None:values[field]=getattr(previous,field)
    if not re.search(r'(?:under|below|budget|for|₹|rs\.?)\s*\d|\d+\s*(?:mein|tak|rupees)',q):values['max_budget']=previous.max_budget
    if not re.search(r'\d+(?:\.\d+)?\s*(?:km|kilomet)',q):values['radius_km']=previous.radius_km
    if 'delivery' not in q and 'dine' not in q:values['mode']=previous.mode
    if intent.party_size==1:values['party_size']=previous.party_size
    if not intent.open_now:values['open_now']=previous.open_now
    return Intent.model_validate(values)

def confidence(dish,restaurant):
    observed=dish.get('source_observed_at') or dish.get('verified_at')
    try:
        date=datetime.fromisoformat(observed.replace('Z','+00:00')) if observed else None
        if date and not date.tzinfo:date=date.replace(tzinfo=timezone.utc)
        age=max(0,(datetime.now(timezone.utc)-date).days) if date else None
    except (ValueError,TypeError):age=None
    return {'level':'sample' if restaurant['sample'] else 'source-listed' if dish.get('source_expires_at') else 'owner-supplied',
            'label':'Fictional sample' if restaurant['sample'] else 'Source-listed · confirm current price' if dish.get('source_expires_at') else 'Owner-supplied · unverified',
            'observed_at':observed,'age_days':age,'may_have_changed':age is None or age>30,
            'independently_verified':False}

def verdict(data,intent):
    from urllib.parse import urlencode
    rows=data.get('results',[])
    for row in rows:
        row['confidence']=confidence(row['dish'],row['restaurant'])
        row['opening']=opening_status(row['restaurant'].get('opening_hours'))
        text=row['restaurant']['name']+' '+(intent.dish or intent.cuisine or '')+' Mumbai'
        row['platform_links']={'zomato':'https://www.zomato.com/mumbai/restaurants?'+urlencode({'q':text}),
                               'swiggy':'https://www.swiggy.com/search?'+urlencode({'query':text}),
                               'presence':'Not checked; links search the platforms'}
    headline=(f"Haan, ₹{rows[0]['dish']['price_paise']/100:g} ka listed option mila." if rows else 'Abhi confirmed priced match nahi mila.')
    if rows and not intent.dish and not intent.cuisine:headline='Explore listed menus near you.'
    alternatives=data.get('alternatives',[])
    if not rows and alternatives:headline=f"Cheapest listed match ₹{alternatives[0]['price_paise']/100:g}; budget se upar."
    return {'alternatives':alternatives,'headline':headline,'match_count':len(rows),'top_ids':[r['restaurant']['id'] for r in rows[:3]],
            'explanation':'Top options match the dish, listed item price and straight-line radius. Confirm current price and availability with the restaurant.' if rows else 'The available catalogue has no priced match for these constraints. Missing data does not prove the dish is unavailable.',
            'party_notice':f"Budget is for {intent.party_size} people; shown amounts are individual menu-item prices, not a confirmed group meal." if intent.party_size>1 else None,
            'mode_notice':'Delivery fees, coupons, availability and minimum orders are not included.' if intent.mode=='delivery' else 'Ordering mode must be confirmed with the restaurant.',
            'follow_ups':['Sabse paas','Aur sasta','Veg only'], 'confidence':'Source observations; no independent restaurant verification'}

def request_research(db,search_record,data,body,intent):
    """Demand schedules existing reviewed sources only; no arbitrary URLs or private platform export."""
    ids=[r['restaurant']['id'] for r in data.get('nearby_unpriced',[])][:10]
    from .database import Restaurant
    from .geo import candidates
    from .agents import AREAS,distance_km
    lat,lng=(body.latitude,body.longitude) if body.latitude is not None else AREAS[intent.location or body.area]
    query=select(Restaurant.id,Restaurant.latitude,Restaurant.longitude).join(CatalogSource,CatalogSource.restaurant_id==Restaurant.id).where(CatalogSource.enabled.is_(True),CatalogSource.kind.in_(['approved_menu','indiarestros_api']),Restaurant.sample.is_(False),Restaurant.owner_id.is_(None))
    nearby=db.execute(candidates(db,query,lat,lng,intent.radius_km).limit(80)).all()
    ids+= [row.id for row in sorted(nearby,key=lambda row:distance_km(lat,lng,row.latitude,row.longitude)) if distance_km(lat,lng,row.latitude,row.longitude)<=intent.radius_km and row.id not in ids][:10]
    if not ids:return {'state':'unavailable','message':'No approved nearby source can fill this gap. Cached results remain available.'}
    sources=db.scalars(select(CatalogSource).where(CatalogSource.restaurant_id.in_(ids),CatalogSource.enabled.is_(True),CatalogSource.kind.in_(['approved_menu','indiarestros_api'])).limit(20)).all()
    jobs=[];cutoff=(datetime.now(timezone.utc)-timedelta(minutes=30)).isoformat()
    for source in sources:
        if len(jobs)>=3:break
        latest=db.scalar(select(CatalogJob).where(CatalogJob.source_id==source.id).order_by(CatalogJob.id.desc()).limit(1))
        if latest and latest.state in ('running','queued'):jobs.append(latest.id);continue
        if latest and latest.finished_at and latest.finished_at>cutoff:continue
        job=CatalogJob(source_id=source.id);db.add(job)
        try:db.flush();jobs.append(job.id)
        except Exception:db.rollback();return {'state':'unavailable','message':'Source refresh already scheduled. Try again shortly.'}
    if not jobs:return {'state':'unavailable','message':'No approved source is ready for live research. Cached results remain available; missing menus are not invented.'}
    rid=uuid.uuid4().hex;db.add(ResearchRequest(id=rid,search_id=search_record.id,job_ids=json.dumps(jobs)));db.commit()
    token=jwt.encode({'aud':'biteai-research','id':rid,'uid':search_record.user_id or 0,'exp':datetime.now(timezone.utc)+timedelta(minutes=15)},SECRET,algorithm='HS256')
    return {'state':'queued','token':token,'message':f'Munshi queued {len(jobs)} approved source checks. Cached verdict is ready now; new data will update this search.'}

async def stream_search(body,user_id):
    queue=asyncio.Queue(maxsize=32);loop=asyncio.get_running_loop()
    def emit(name,data):
        if not queue.full():queue.put_nowait((name,data))
    def progress(name,data):loop.call_soon_threadsafe(emit,name,data)
    async def work():
        started=time.monotonic()
        try:
            intent,parser=await understand(body.query,body.budget,body.radius_km)
            intent=continued_intent(body.query,intent,body.context)
            emit('intent',{'agent':'Saarthi','intent':intent.model_dump(),'message':'Samjha: '+(intent.dish or intent.cuisine or 'nearby food')})
            def lookup():
                from .main import search_database
                with Session() as db:
                    user=db.get(User,user_id) if user_id else None
                    return search_database(body,intent,parser,user,db,progress)
            from starlette.concurrency import run_in_threadpool
            result=await run_in_threadpool(lookup)
            emit('verdict',result)
        except asyncio.CancelledError:raise
        except Exception as error:
            emit('error',{'message':error.detail if isinstance(error,HTTPException) and isinstance(error.detail,str) else 'Search could not finish. Please retry.'})
        finally:emit('done',{})
    result_box={}
    async def events():
        task=asyncio.create_task(work());result=None
        try:
            yield 'event: status\ndata: '+json.dumps({'agent':'Saarthi','message':'Reading your craving…'})+'\n\n'
            while True:
                try:name,data=await asyncio.wait_for(queue.get(),timeout=10)
                except asyncio.TimeoutError:yield ': keep-alive\n\n';continue
                if name=='verdict':result=data;result_box.update(data)
                if name=='done':break
                yield 'event: '+name+'\ndata: '+json.dumps(jsonable_encoder(data),ensure_ascii=False)+'\n\n'
        finally:
            if not task.done():task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    async def finish_research():
        if RESEARCH_GATE.locked():return
        async with RESEARCH_GATE:
            from starlette.concurrency import run_in_threadpool
            await run_in_threadpool(run_research)
    def run_research():
        result=result_box
        # Work is persisted before starting network research. The worker also recovers queued jobs.
        if result and result.get('research',{}).get('token'):
            claims=jwt.decode(result['research']['token'],SECRET,algorithms=['HS256'],audience='biteai-research')
            with Session() as db:row=db.get(ResearchRequest,claims['id']);ids=json.loads(row.job_ids) if row else []
            from .catalog_worker import run_one
            for job_id in ids:
                # The worker uses synchronous SQLAlchemy and parsing between HTTP
                # awaits. Give it a separate event loop in the background thread;
                # otherwise these operations stall health/search/status requests.
                try:asyncio.run(asyncio.wait_for(run_one(job_id=job_id),timeout=45))
                except (Exception,asyncio.CancelledError):
                    from sqlalchemy import update
                    with Session() as db:
                        db.execute(update(CatalogJob).where(CatalogJob.id==job_id,CatalogJob.state=='running').values(state='queued',error='Research budget exceeded; durable worker will retry',available_at=now()));db.commit()
                    break
    from starlette.background import BackgroundTask
    return StreamingResponse(events(),background=BackgroundTask(finish_research),media_type='text/event-stream',headers={'Cache-Control':'no-store, no-transform','Content-Encoding':'identity','X-Accel-Buffering':'no'})

@router.get('/research/{token}')
def research_status(token:str,user=Depends(optional_user),db=Depends(db_session)):
    try:claims=jwt.decode(token,SECRET,algorithms=['HS256'],audience='biteai-research',options={'require':['exp','id','uid']})
    except jwt.PyJWTError:raise HTTPException(400,'Research status expired; search again') from None
    if claims['uid'] and (not user or claims['uid']!=user.id):raise HTTPException(403,'Research belongs to another account')
    row=db.get(ResearchRequest,claims['id'])
    if not row:raise HTTPException(404,'Research request no longer available')
    jobs=db.scalars(select(CatalogJob).where(CatalogJob.id.in_(json.loads(row.job_ids)))).all()
    terminal=bool(jobs) and all(j.state in ('succeeded','failed') for j in jobs)
    return {'state':'completed' if terminal else 'running','succeeded':sum(j.state=='succeeded' for j in jobs),'failed':sum(j.state=='failed' for j in jobs),
            'message':'Approved source checks finished; refreshed results may still have no matching dish.' if terminal else 'Munshi is checking approved sources. Cached results remain available.'}

@router.get('/agents/activity')
def activity(db=Depends(db_session)):
    jobs=db.execute(select(CatalogJob.state,func.count()).group_by(CatalogJob.state)).all()
    runs=db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(20)).all()
    return {'jobs':dict(jobs),'agents':[{'id':r.id,'agent':r.agent,'state':r.status,'latency_ms':r.latency_ms,'cost_microrupees':r.cost_microrupees,'created_at':r.created_at} for r in runs],
            'notice':'Actual recorded runs. No individual search text, account details or private platform responses are exposed.'}

def admin(user=Depends(current_user)):
    if user.role!='admin':raise HTTPException(403,'Administrator role required')
    return user

@router.get('/admin/quality')
def quality(user=Depends(admin),db=Depends(db_session)):
    rows=db.execute(select(MenuItem,MenuEvidence).join(MenuEvidence).where((MenuEvidence.active.is_(False)) | (MenuEvidence.expires_at<now()) | MenuEvidence.method.startswith('Gemini')).order_by(MenuItem.id).limit(50)).all()
    return [{'id':item.id,'restaurant_id':item.restaurant_id,'name':item.name,'price_paise':item.price_paise,'source':item.source,'active':ev.active,'expires_at':ev.expires_at,'method':ev.method,'excerpt':ev.excerpt} for item,ev in rows]

from pydantic import BaseModel,Field
from typing import Literal
class Review(BaseModel):
    decision:Literal['approve','reject']
    note:str=Field(min_length=5,max_length=300)
@router.post('/admin/quality/{mid}')
def review(mid:int,body:Review,user=Depends(admin),db=Depends(db_session)):
    evidence=db.scalar(select(MenuEvidence).where(MenuEvidence.menu_item_id==mid).with_for_update());item=db.get(MenuItem,mid)
    if not evidence or not item:raise HTTPException(404,'Source-backed menu item not found')
    if body.decision=='approve' and evidence.expires_at<=now():raise HTTPException(409,'Expired prices require a new source observation before approval')
    if body.decision=='approve' and not evidence.active and not evidence.method.startswith('Gemini'):raise HTTPException(409,'Withdrawn source prices require a new source observation')
    evidence.active=body.decision=='approve';item.available=evidence.active
    db.add(IngestionLog(restaurant_id=item.restaurant_id,source='admin-quality-review',trace=json.dumps({'administrator_id':user.id,'menu_item_id':mid,'decision':body.decision,'note':body.note,'at':now()})));db.commit()
    return {'active':evidence.active,'notice':'Review changes visibility only; it does not establish restaurant verification.'}


def save_bronze(db,source_id,html):
    import hashlib
    digest=hashlib.sha256(html.encode()).hexdigest();identifier=hashlib.sha256((str(source_id)+digest).encode()).hexdigest()
    if db.get(BronzeArtifact,identifier):return
    # Explicit bounded retention; never let public research consume the database quota.
    if len(html.encode())>1_000_000:return
    if (db.scalar(select(func.count()).select_from(BronzeArtifact)) or 0)>=50:return
    db.add(BronzeArtifact(id=identifier,source_id=source_id,content_hash=digest,content=html));db.flush()
