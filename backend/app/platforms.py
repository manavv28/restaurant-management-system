"""Official, per-user Swiggy read tools. No bulk export, order, address or payment tools."""
import base64,hashlib,hmac,json,math,os,re,secrets,time
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from urllib.parse import urlencode,urlsplit
import httpx,jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter,Depends,HTTPException,Request,Response,Query,BackgroundTasks
from pydantic import BaseModel,Field
from sqlalchemy import select,delete
from starlette.responses import RedirectResponse
from .database import Session,ProviderConnection,ProviderOAuthState,now
from .security import SECRET,current_user,optional_user,db_session
from .account_security import throttle
from .schemas import SearchInput
from .agents import AREAS,parse_local

router=APIRouter(prefix='/platforms',tags=['Delivery platforms'])
ORIGIN='https://mcp.swiggy.com'
TOOLS={'search_restaurants','search_menu','get_restaurant_menu'}
CALLBACK='/api/platforms/swiggy/callback'

def seal(value,user_id):
    key=hmac.new(SECRET.encode(),b'BiteAI/provider-tokens/v1',hashlib.sha256).digest()
    nonce=secrets.token_bytes(12)
    body=AESGCM(key).encrypt(nonce,json.dumps(value,separators=(',',':')).encode(),str(user_id).encode())
    return base64.urlsafe_b64encode(nonce+body).decode()

def unseal(value,user_id):
    try:
        raw=base64.urlsafe_b64decode(value)
        key=hmac.new(SECRET.encode(),b'BiteAI/provider-tokens/v1',hashlib.sha256).digest()
        return json.loads(AESGCM(key).decrypt(raw[:12],raw[12:],str(user_id).encode()))
    except Exception:raise HTTPException(401,'Please reconnect Swiggy') from None

def public_base():
    base=os.getenv('PUBLIC_APP_URL','http://localhost:3000').rstrip('/')
    parsed=urlsplit(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise HTTPException(503,'Provider callback is not configured')
    if os.getenv('APP_ENV')=='production':
        if base!='https://restaurant-management-system-qxtx.vercel.app':raise HTTPException(503,'Provider callback is not configured')
    elif parsed.scheme!='https' and not(parsed.scheme=='http' and parsed.hostname=='localhost'):
        raise HTTPException(503,'Provider callback requires HTTPS or localhost')
    return base

def enabled():
    return os.getenv('SWIGGY_MCP_ENABLED','false').lower()=='true' and (os.getenv('APP_ENV')!='production' or os.getenv('SWIGGY_MCP_PRODUCTION_APPROVED','false').lower()=='true')

def require_enabled():
    if not enabled():raise HTTPException(503,'Swiggy live search is not available yet. You can browse Swiggy directly.')

def private(response):
    response.headers['Cache-Control']='no-store';response.headers['Referrer-Policy']='no-referrer'

def upstream(path,payload=None,token=None):
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            with client.stream('POST',ORIGIN+path,json=payload,headers=headers) as r:
                if r.status_code in (401,419) or (r.status_code==400 and path=='/auth/token'):raise HTTPException(401,'Please reconnect Swiggy')
                if r.status_code==429:
                    wait=r.headers.get('Retry-After','60')
                    if not wait.isdigit():wait='60'
                    raise HTTPException(429,'Swiggy is busy. Please try again later.',headers={'Retry-After':wait})
                if not r.is_success:raise HTTPException(503,'Swiggy could not complete the request. Please try again later.')
                body=bytearray()
                for chunk in r.iter_bytes():
                    body.extend(chunk)
                    if len(body)>1_000_000:raise HTTPException(502,'Swiggy returned an oversized response')
        result=json.loads(body) if body else {}
        if not isinstance(result,dict):raise HTTPException(502,'Swiggy returned an invalid response')
        return result
    except (httpx.HTTPError,ValueError):raise HTTPException(503,'Swiggy could not complete the request. Please try again later.') from None

@router.get('/status')
def status(response:Response,user=Depends(optional_user),db=Depends(db_session)):
    private(response)
    connection=db.get(ProviderConnection,(user.id,'swiggy')) if user else None
    from .zomato import enabled as zomato_enabled
    zomato=db.get(ProviderConnection,(user.id,'zomato')) if user else None
    return {'swiggy':{'available':enabled(),'connected':bool(connection and connection.retain_until>now()),'connection_expires_at':connection.expires_at if connection else None},'zomato':{'available':False,'can_connect':zomato_enabled(),'connected':bool(zomato and zomato.retain_until>now()),'mode':'schema_verification_pending','message':'Account linking is available once approved. Live menu search awaits authenticated tool-schema verification.'}}

@router.post('/swiggy/connect')
def connect(request:Request,response:Response,user=Depends(current_user),db=Depends(db_session)):
    private(response);require_enabled();throttle(db,'swiggy-connect',str(user.id),limit=5,seconds=600)
    redirect=public_base()+CALLBACK
    # Public OAuth client; the provider handles phone + OTP on its own domain.
    registration=upstream('/auth/register',{'client_name':'BiteAI','redirect_uris':[redirect],'grant_types':['authorization_code','refresh_token'],'response_types':['code'],'token_endpoint_auth_method':'none'})
    client_id=registration.get('client_id')
    if not isinstance(client_id,str) or not 1<=len(client_id)<=500:raise HTTPException(502,'Swiggy registration could not be completed')
    verifier=secrets.token_urlsafe(32);state=secrets.token_urlsafe(32)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    db.execute(delete(ProviderOAuthState).where(ProviderOAuthState.user_id==user.id))
    db.add(ProviderOAuthState(id=hashlib.sha256(state.encode()).hexdigest(),user_id=user.id,session_id=request.state.session_id,
        encrypted_flow=seal({'provider':'swiggy','verifier':verifier,'client_id':client_id,'redirect_uri':redirect},user.id),expires_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()));db.commit()
    return {'authorization_url':ORIGIN+'/auth/authorize?'+urlencode({'response_type':'code','client_id':client_id,'redirect_uri':redirect,'code_challenge':challenge,'code_challenge_method':'S256','scope':'mcp:tools','state':state})}


def save_tokens(db,user_id,tokens,client_id,provider='swiggy'):
    try:
        access=tokens['access_token'];expiry=int(tokens['expires_in'])
        if not isinstance(access,str) or not access or len(access)>20000 or not 0<expiry<=31*86400:raise ValueError()
        if str(tokens.get('token_type','Bearer')).lower()!='bearer':raise ValueError()
        refresh=tokens.get('refresh_token')
        if refresh is not None and (not isinstance(refresh,str) or len(refresh)>20000):raise ValueError()
    except (ValueError,KeyError,TypeError):raise HTTPException(502,'Swiggy returned invalid authorization information') from None
    row=db.get(ProviderConnection,(user_id,provider))
    if not row:row=ProviderConnection(user_id=user_id,provider=provider);db.add(row)
    row.tool_manifest='[]'
    row.retain_until=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat()
    row.encrypted_tokens=seal({'provider':provider,'access_token':access,'refresh_token':refresh,'client_id':client_id},user_id)
    row.expires_at=(datetime.now(timezone.utc)+timedelta(seconds=expiry)).isoformat();db.commit()

@router.get('/swiggy/callback')
def callback(request:Request,background:BackgroundTasks,state:str=Query(default='',max_length=200),code:str=Query(default='',max_length=4000),error:str=Query(default='',max_length=200),user=Depends(current_user),db=Depends(db_session)):
    require_enabled()
    if not state or len(state)>200 or len(code)>4000:raise HTTPException(400,'Invalid Swiggy callback')
    flow=db.scalar(select(ProviderOAuthState).where(ProviderOAuthState.id==hashlib.sha256(state.encode()).hexdigest(),ProviderOAuthState.user_id==user.id,ProviderOAuthState.session_id==request.state.session_id,ProviderOAuthState.expires_at>now()).with_for_update())
    if not flow:db.rollback();raise HTTPException(400,'Swiggy connection expired. Please connect again.')
    details=unseal(flow.encrypted_flow,user.id)
    if details.get('provider')!='swiggy':db.rollback();raise HTTPException(400,'Incorrect provider callback')
    db.delete(flow);db.commit()
    redirect=public_base()+'/?swiggy='
    if error:
        response=RedirectResponse(redirect+'cancelled',status_code=303);private(response);return response
    if not code:raise HTTPException(400,'Missing Swiggy authorization code')
    tokens=upstream('/auth/token',{'grant_type':'authorization_code','code':code,'code_verifier':details['verifier'],'client_id':details['client_id'],'redirect_uri':details['redirect_uri']})
    save_tokens(db,user.id,tokens,details['client_id'])
    background.add_task(capture_manifest,user.id)
    response=RedirectResponse(redirect+'connected',status_code=303);private(response);return response

def capture_manifest(user_id):
    try:
        with Session() as db:
            row=db.get(ProviderConnection,(user_id,'swiggy'))
            if not row or row.expires_at<=now():return
            tokens=unseal(row.encrypted_tokens,user_id);db.commit()
            tools=read_tool(tokens['access_token'],None,{},list_tools=True).get('tools')
            if not isinstance(tools,list) or len(tools)>100:return
            manifest=[{key:t[key] for key in ('name','description','inputSchema','outputSchema','annotations') if key in t} for t in tools if isinstance(t,dict)]
            row=db.get(ProviderConnection,(user_id,'swiggy'))
            if row:row.tool_manifest=json.dumps(manifest,ensure_ascii=False);db.commit()
    except (HTTPException,KeyError):return

@router.delete('/swiggy')
def disconnect(response:Response,user=Depends(current_user),db=Depends(db_session)):
    private(response);row=db.get(ProviderConnection,(user.id,'swiggy'));token=None
    if row:
        try:token=unseal(row.encrypted_tokens,user.id).get('access_token')
        except HTTPException:pass
        db.delete(row)
    db.execute(delete(ProviderOAuthState).where(ProviderOAuthState.user_id==user.id));db.commit()
    remote_revoked=False
    if token:
        try:upstream('/auth/logout',token=token);remote_revoked=True
        except HTTPException:pass
    return {'disconnected':True,'provider_revoked':remote_revoked,'message':'Swiggy disconnected from BiteAI.' if remote_revoked or not token else 'Disconnected locally. You can also revoke access in Swiggy.'}

def access_token(db,user_id,force=False):
    row=db.scalar(select(ProviderConnection).where(ProviderConnection.user_id==user_id,ProviderConnection.provider=='swiggy').with_for_update())
    if not row:db.commit();raise HTTPException(401,'Connect Swiggy to use live search')
    if row.retain_until<=now():
        db.delete(row);db.commit();raise HTTPException(401,'Please reconnect Swiggy')
    tokens=unseal(row.encrypted_tokens,user_id)
    if force or row.expires_at<=(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat():
        if not tokens.get('refresh_token'):db.commit();raise HTTPException(401,'Please reconnect Swiggy')
        try:
            updated=upstream('/auth/token',{'grant_type':'refresh_token','refresh_token':tokens['refresh_token']})
            if not updated.get('refresh_token'):raise HTTPException(502,'Swiggy token refresh was incomplete')
            save_tokens(db,user_id,updated,tokens['client_id']);return updated['access_token']
        except HTTPException as exc:
            db.rollback()
            if exc.status_code==401:
                db.execute(delete(ProviderConnection).where(ProviderConnection.user_id==user_id,ProviderConnection.provider=='swiggy'));db.commit()
            raise
    db.commit();return tokens['access_token']


def rpc_result(body,request_id,content_type):
    if 'text/event-stream' in content_type:
        messages=[]
        for event in body.replace('\r\n','\n').split('\n\n'):
            value='\n'.join(line[5:].lstrip() for line in event.splitlines() if line.startswith('data:'))
            if value:messages.append(json.loads(value))
    else:messages=[json.loads(body)]
    message=next((m for m in messages if isinstance(m,dict) and m.get('id')==request_id),None)
    if not message:raise HTTPException(502,'Swiggy could not complete the request')
    if message.get('error'):
        if isinstance(message['error'],dict) and message['error'].get('code')==-32001:raise HTTPException(401,'Please reconnect Swiggy')
        raise HTTPException(502,'Swiggy could not complete the tool request')
    result=message.get('result',{})
    if not isinstance(result,dict):raise HTTPException(502,'Swiggy returned an invalid result')
    return result

def read_tool(token,name,arguments,provider='swiggy',list_tools=False):
    if not list_tools and (provider!='swiggy' or name not in TOOLS):raise HTTPException(400,'Only restaurant and menu browsing is supported')
    headers={'Authorization':'Bearer '+token,'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            deadline=time.monotonic()+25
            def send(payload,notification=False):
                if time.monotonic()>deadline:raise HTTPException(504,'Swiggy is taking longer than expected. Please retry.')
                with client.stream('POST',(ORIGIN+'/food' if provider=='swiggy' else 'https://mcp-server.zomato.com/mcp'),headers=headers,json=payload) as r:
                    if r.status_code in (401,419):raise HTTPException(401,'Please reconnect Swiggy')
                    if r.status_code==429:
                        retry=r.headers.get('Retry-After','60');retry=retry if retry.isdigit() else '60'
                        raise HTTPException(429,'Swiggy is busy. Please try again later.',headers={'Retry-After':retry})
                    if not r.is_success:raise HTTPException(503,'Swiggy live search is temporarily unavailable')
                    if r.headers.get('mcp-session-id'):headers['Mcp-Session-Id']=r.headers['mcp-session-id']
                    if notification:return {}
                    body=bytearray();events=bytearray();is_sse='text/event-stream' in r.headers.get('content-type','')
                    for chunk in r.iter_bytes():
                        if time.monotonic()>deadline:raise HTTPException(504,'Delivery platform is taking longer than expected. Please retry.')
                        body.extend(chunk)
                        if len(body)>3_000_000:raise HTTPException(502,'Delivery platform returned too much data. Try a narrower search.')
                        if is_sse:
                            events.extend(chunk);events[:]=events.replace(b'\r\n',b'\n')
                            while b'\n\n' in events:
                                frame,remainder=bytes(events).split(b'\n\n',1);events[:]=remainder
                                value='\n'.join(line[5:].lstrip() for line in frame.decode().splitlines() if line.startswith('data:'))
                                if not value:continue
                                message=json.loads(value)
                                if isinstance(message,dict) and message.get('id')==payload['id']:
                                    return rpc_result(json.dumps(message),payload['id'],'application/json')
                    return rpc_result(body.decode(),payload['id'],r.headers.get('content-type',''))
            init=send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'BiteAI','version':'0.1.0'}}})
            version=init.get('protocolVersion')
            if version not in ('2025-03-26','2025-06-18','2025-11-25'):raise HTTPException(502,'Swiggy live search is temporarily unavailable')
            headers['MCP-Protocol-Version']=version
            send({'jsonrpc':'2.0','method':'notifications/initialized'},True)
            result=send({'jsonrpc':'2.0','id':2,'method':'tools/list' if list_tools else 'tools/call','params':{} if list_tools else {'name':name,'arguments':arguments}})
            if list_tools:return result
            if result.get('isError'):raise HTTPException(502,'Swiggy could not complete the search')
            envelope=result.get('structuredContent')
            if not isinstance(envelope,dict) or envelope.get('success') is not True or not isinstance(envelope.get('data'),dict):
                raise HTTPException(502,'Swiggy did not return structured search data')
            return envelope['data']
    except (httpx.HTTPError,ValueError,UnicodeError):raise HTTPException(503,'Swiggy live search is temporarily unavailable') from None

def call(db,user_id,name,arguments):
    require_enabled();token=access_token(db,user_id)
    try:return read_tool(token,name,arguments)
    except HTTPException as exc:
        if exc.status_code!=401:raise
        token=access_token(db,user_id,True)
        return read_tool(token,name,arguments)

@router.post('/swiggy/search')
def live_search(body:SearchInput,response:Response,user=Depends(current_user),db=Depends(db_session)):
    private(response);require_enabled();throttle(db,'swiggy-read',str(user.id),limit=20)
    intent=parse_local(body.query,body.budget,body.radius_km);area=intent.location or body.area
    if area not in AREAS or (body.latitude is None)!=(body.longitude is None):raise HTTPException(422,'Choose a Mumbai area or provide both coordinates')
    query=intent.cuisine or intent.dish or body.query.strip()
    if not query:raise HTTPException(422,'Enter a dish or cuisine to search Swiggy')
    lat,lng=(body.latitude,body.longitude) if body.latitude is not None else AREAS[area]
    data=call(db,user.id,'search_restaurants',{'query':query,'latitude':lat,'longitude':lng})
    restaurants=[]
    rows=data.get('restaurants',[])
    if not isinstance(rows,list):raise HTTPException(502,'Swiggy returned invalid restaurant data')
    for r in rows[:100]:
        if not isinstance(r,dict):continue
        distance=r.get('distanceKm');rid=r.get('id');name=r.get('name')
        if r.get('availabilityStatus')!='OPEN' or not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z0-9:_-]{1,150}',rid) or not isinstance(name,str):continue
        if isinstance(distance,bool) or not isinstance(distance,(int,float)) or not math.isfinite(distance) or not 0<=distance<=intent.radius_km:continue
        selection=jwt.encode({'aud':'biteai-swiggy-selection','sub':str(user.id),'rid':rid,'latitude':lat,'longitude':lng,'budget':intent.max_budget,'exp':datetime.now(timezone.utc)+timedelta(minutes=10)},SECRET,algorithm='HS256')
        restaurants.append({'id':rid,'name':name[:200],'area':str(r.get('areaName') or '')[:150],'distance_km':distance,'selection':selection})
    return {'provider':'Swiggy','restaurants':restaurants[:20],'notice':'Provider-reported delivery distance. Select a restaurant to check its dish prices. Fees and taxes may differ.','has_more':bool(data.get('hasMore'))}

class MenuRequest(BaseModel):
    selection:str=Field(max_length=4000)
    query:str=Field(min_length=1,max_length=500)

@router.post('/swiggy/menu')
def live_menu(body:MenuRequest,response:Response,user=Depends(current_user),db=Depends(db_session)):
    private(response);require_enabled();throttle(db,'swiggy-read',str(user.id),limit=20)
    if not body.query.strip():raise HTTPException(422,'Enter a dish to check its menu')
    try:
        selection=jwt.decode(body.selection,SECRET,algorithms=['HS256'],audience='biteai-swiggy-selection',options={'require':['exp','sub','rid','latitude','longitude','budget']})
        if selection['sub']!=str(user.id):raise ValueError()
    except (jwt.PyJWTError,ValueError):raise HTTPException(400,'Select a Swiggy restaurant again') from None
    intent=parse_local(body.query)
    menu_query=intent.dish or intent.cuisine or body.query.strip()
    data=call(db,user.id,'search_menu',{'query':menu_query,'restaurantIdOfAddedItem':selection['rid'],'latitude':selection['latitude'],'longitude':selection['longitude']})
    items=[];unit=os.getenv('SWIGGY_MCP_PRICE_UNIT','unknown')
    rows=data.get('items',[])
    if not isinstance(rows,list):raise HTTPException(502,'Swiggy returned invalid menu data')
    for row in rows[:100]:
        if not isinstance(row,dict):continue
        if row.get('restaurant_id')!=selection['rid'] or not isinstance(row.get('name'),str):continue
        amount=None;stock=row.get('inStock')
        # Units must be confirmed with the provider; do not guess INR versus paise.
        if unit in ('rupees','paise') and stock in (1,True) and row.get('hasVariants') is False and row.get('hasAddons') is False:
            try:
                value=Decimal(str(row['price']))*(100 if unit=='rupees' else 1)
                if value.is_finite() and 0<value<=10000000 and value==value.to_integral_value():amount=int(value)
            except (KeyError,InvalidOperation,ValueError):pass
        items.append({'name':row['name'][:200],'price_paise':amount,'within_budget':amount<=selection['budget']*100 if amount else None,'available':stock in (1,True),'price_status':'Live Swiggy listing; fees and taxes excluded' if amount else 'Confirm price and options on Swiggy'})
    return {'provider':'Swiggy','items':items,'has_more':bool(data.get('hasMore')),'notice':'Results serve this search only and are not copied into the public catalog.'}
