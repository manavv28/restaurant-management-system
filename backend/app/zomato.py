"""Approved Zomato OAuth bridge; business tools await the authenticated contract."""
import base64,hashlib,json,os,secrets
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter,Depends,HTTPException,Request,Response,Query,BackgroundTasks
from starlette.responses import RedirectResponse
from sqlalchemy import select,delete
from .database import Session,ProviderConnection,ProviderOAuthState,now
from .security import current_user,db_session
from .account_security import throttle
from .platforms import seal,unseal,public_base,private,save_tokens,read_tool

router=APIRouter(prefix='/platforms/zomato',tags=['Delivery platforms'])
ORIGIN='https://mcp-server.zomato.com'

def enabled():
    return os.getenv('ZOMATO_MCP_ENABLED','false').lower()=='true' and (os.getenv('APP_ENV')!='production' or os.getenv('ZOMATO_MCP_PRODUCTION_APPROVED','false').lower()=='true')

def require_enabled():
    if not enabled():raise HTTPException(503,'Zomato connection is not available yet. Browse Zomato directly.')

def request_token(path,payload):
    if path not in ('/register','/token'):raise ValueError('Unsupported provider endpoint')
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            with client.stream('POST',ORIGIN+path,headers={'Accept':'application/json'},**({'data':payload} if path=='/token' else {'json':payload})) as response:
                if response.status_code in (401,403) or (path=='/token' and response.status_code==400):raise HTTPException(401,'Please connect Zomato again')
                if response.status_code==429:
                    retry=response.headers.get('Retry-After','60');retry=retry if retry.isdigit() else '60'
                    raise HTTPException(429,'Zomato is busy. Please try again later.',headers={'Retry-After':retry})
                if not response.is_success:raise HTTPException(503,'Zomato could not complete the connection')
                body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>1_000_000:raise HTTPException(502,'Zomato returned an oversized response')
        result=json.loads(body)
        if not isinstance(result,dict):raise ValueError()
        return result
    except (httpx.HTTPError,ValueError):raise HTTPException(503,'Zomato could not complete the connection') from None

@router.post('/connect')
def connect(request:Request,response:Response,user=Depends(current_user),db=Depends(db_session)):
    private(response);require_enabled();throttle(db,'zomato-connect',str(user.id),limit=5,seconds=600)
    redirect=public_base()+'/api/platforms/zomato/callback'
    client=request_token('/register',{'client_name':'BiteAI','redirect_uris':[redirect],'grant_types':['authorization_code','refresh_token'],'response_types':['code'],'token_endpoint_auth_method':'none'})
    client_id=client.get('client_id')
    if not isinstance(client_id,str) or not 1<=len(client_id)<=500:raise HTTPException(502,'Zomato client registration failed')
    verifier=secrets.token_urlsafe(32);state=secrets.token_urlsafe(32);challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    db.execute(delete(ProviderOAuthState).where(ProviderOAuthState.user_id==user.id))
    db.add(ProviderOAuthState(id=hashlib.sha256(state.encode()).hexdigest(),user_id=user.id,session_id=request.state.session_id,encrypted_flow=seal({'provider':'zomato','verifier':verifier,'client_id':client_id,'redirect_uri':redirect},user.id),expires_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()));db.commit()
    return {'authorization_url':ORIGIN+'/authorize?'+urlencode({'response_type':'code','client_id':client_id,'redirect_uri':redirect,'code_challenge':challenge,'code_challenge_method':'S256','scope':'mcp:tools','state':state})}


def capture_manifest(user_id):
    try:
        with Session() as db:
            connection=db.get(ProviderConnection,(user_id,'zomato'))
            if not connection or connection.expires_at<=now():return
            tokens=unseal(connection.encrypted_tokens,user_id);db.commit()
            manifest=read_tool(tokens['access_token'],None,{},provider='zomato',list_tools=True).get('tools')
            if not isinstance(manifest,list) or len(manifest)>100:return
            cleaned=[{k:tool[k] for k in ('name','description','inputSchema','outputSchema','annotations') if k in tool} for tool in manifest if isinstance(tool,dict)]
            row=db.get(ProviderConnection,(user_id,'zomato'))
            if row:row.tool_manifest=json.dumps(cleaned,ensure_ascii=False);db.commit()
    except (HTTPException,KeyError):return

@router.get('/callback')
def callback(request:Request,background:BackgroundTasks,state:str=Query(default='',max_length=200),code:str=Query(default='',max_length=4000),error:str=Query(default='',max_length=200),user=Depends(current_user),db=Depends(db_session)):
    require_enabled()
    flow=db.scalar(select(ProviderOAuthState).where(ProviderOAuthState.id==hashlib.sha256(state.encode()).hexdigest(),ProviderOAuthState.user_id==user.id,ProviderOAuthState.session_id==request.state.session_id,ProviderOAuthState.expires_at>now()).with_for_update())
    if not flow:db.rollback();raise HTTPException(400,'Zomato connection expired. Please connect again.')
    details=unseal(flow.encrypted_flow,user.id)
    if details.get('provider')!='zomato':db.rollback();raise HTTPException(400,'Incorrect provider callback')
    db.delete(flow);db.commit()
    if not error:
        if not code:raise HTTPException(400,'Missing Zomato authorization code')
        tokens=request_token('/token',{'grant_type':'authorization_code','code':code,'code_verifier':details['verifier'],'client_id':details['client_id'],'redirect_uri':details['redirect_uri']})
        save_tokens(db,user.id,tokens,details['client_id'],provider='zomato');background.add_task(capture_manifest,user.id)
    response=RedirectResponse(public_base()+'/?zomato='+('cancelled' if error else 'connected'),status_code=303);private(response);return response

@router.delete('')
def disconnect(response:Response,user=Depends(current_user),db=Depends(db_session)):
    private(response);db.execute(delete(ProviderConnection).where(ProviderConnection.user_id==user.id,ProviderConnection.provider=='zomato'));db.execute(delete(ProviderOAuthState).where(ProviderOAuthState.user_id==user.id));db.commit()
    return {'disconnected':True,'provider_revoked':False,'message':'Zomato disconnected from BiteAI. Revoke provider-side access in Zomato if needed.'}
