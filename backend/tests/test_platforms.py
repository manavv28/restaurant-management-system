"""Synthetic provider contracts only; no actual Swiggy account or order is used."""
import json,hashlib
from urllib.parse import urlsplit,parse_qs
from datetime import datetime,timedelta,timezone
import httpx,pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from test_api import client,account
from app import platforms
from app.database import Session,ProviderConnection,ProviderOAuthState,MenuItem,Search,IngestionLog

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('SWIGGY_MCP_ENABLED','true');monkeypatch.setenv('APP_ENV','development');monkeypatch.setenv('PUBLIC_APP_URL','http://localhost:3000');monkeypatch.setenv('SWIGGY_MCP_PRICE_UNIT','rupees')

@pytest.fixture
def provider(monkeypatch):
    calls=[]
    monkeypatch.setattr(platforms,'capture_manifest',lambda user_id:None)
    def upstream(path,payload=None,token=None):
        calls.append((path,payload,token))
        if path=='/auth/register':return {'client_id':'synthetic-client'}
        if path=='/auth/token':return {'access_token':'synthetic-private-access','refresh_token':'synthetic-private-refresh','expires_in':3600,'token_type':'Bearer'}
        return {}
    monkeypatch.setattr(platforms,'upstream',upstream)
    return calls

def linked(c,headers):
    start=c.post('/platforms/swiggy/connect',headers=headers);assert start.status_code==200,start.text
    parsed=parse_qs(urlsplit(start.json()['authorization_url']).query)
    result=c.get('/platforms/swiggy/callback',params={'code':'synthetic-code','state':parsed['state'][0]},headers=headers,follow_redirects=False)
    assert result.status_code==303,result.text
    return parsed

def test_disabled_and_provider_policy(client,monkeypatch):
    monkeypatch.delenv('SWIGGY_MCP_ENABLED',raising=False)
    h=account(client)
    assert client.get('/platforms/status').json()['zomato']['available'] is False
    assert client.post('/platforms/swiggy/connect',headers=h).status_code==503
    monkeypatch.setenv('SWIGGY_MCP_ENABLED','true');monkeypatch.setenv('APP_ENV','production');monkeypatch.delenv('SWIGGY_MCP_PRODUCTION_APPROVED',raising=False)
    assert client.get('/platforms/status').json()['swiggy']['available'] is False
    assert client.post('/platforms/swiggy/search',headers=h,json={'query':'noodles'}).status_code==503

def test_pkce_encrypted_storage_callback_replay_and_account_isolation(client,configured,provider):
    first=account(client);second=account(client,'second@example.test')
    start=client.post('/platforms/swiggy/connect',headers=first);params=parse_qs(urlsplit(start.json()['authorization_url']).query);state=params['state'][0]
    assert params['code_challenge_method']==['S256'];assert params['scope']==['mcp:tools']
    with Session() as db:
        flow=db.scalar(select(ProviderOAuthState));assert 'verifier' not in flow.encrypted_flow
        decoded=platforms.unseal(flow.encrypted_flow,flow.user_id)
        import base64
        assert params['code_challenge']==[base64.urlsafe_b64encode(hashlib.sha256(decoded['verifier'].encode()).digest()).decode().rstrip('=')]
        with pytest.raises(HTTPException):platforms.unseal(flow.encrypted_flow,999999)
    assert client.get('/platforms/swiggy/callback',params={'state':state,'code':'test'},headers=second).status_code==400
    assert client.get('/platforms/swiggy/callback',params={'state':state,'code':'test'},headers=first,follow_redirects=False).status_code==303
    assert client.get('/platforms/swiggy/callback',params={'state':state,'code':'test'},headers=first).status_code==400
    one=client.get('/platforms/status',headers=first);assert one.json()['swiggy']['connected'];assert one.headers['cache-control']=='no-store'
    assert 'synthetic-private' not in one.text
    assert not client.get('/platforms/status',headers=second).json()['swiggy']['connected']
    with Session() as db:
        row=db.scalar(select(ProviderConnection));assert 'synthetic-private' not in row.encrypted_tokens
    assert client.delete('/platforms/swiggy',headers=second).status_code==200
    assert client.get('/platforms/status',headers=first).json()['swiggy']['connected']
    assert client.delete('/platforms/swiggy',headers=first).json()['provider_revoked']
    assert not client.get('/platforms/status',headers=first).json()['swiggy']['connected']

def test_denial_expiry_and_same_session_binding(client,configured,provider):
    h=account(client);state=parse_qs(urlsplit(client.post('/platforms/swiggy/connect',headers=h).json()['authorization_url']).query)['state'][0]
    # A different sign-in session for the same user must not consume the first flow.
    h2={'Authorization':'Bearer '+client.post('/auth/login',json={'email':'food@example.test','password':'secure-test-password'}).json()['token']}
    assert client.get('/platforms/swiggy/callback',params={'state':state,'error':'access_denied'},headers=h2).status_code==400
    denied=client.get('/platforms/swiggy/callback',params={'state':state,'error':'access_denied'},headers=h,follow_redirects=False)
    assert denied.status_code==303 and denied.headers['location'].endswith('swiggy=cancelled')
    state=parse_qs(urlsplit(client.post('/platforms/swiggy/connect',headers=h).json()['authorization_url']).query)['state'][0]
    with Session() as db:
        row=db.scalar(select(ProviderOAuthState));row.expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();db.commit()
    assert client.get('/platforms/swiggy/callback',params={'state':state,'code':'test'},headers=h).status_code==400
    with Session() as db:assert db.scalar(select(func.count()).select_from(ProviderConnection))==0

def test_selected_venue_radius_budget_missing_prices_and_no_catalog_persistence(client,configured,provider,monkeypatch):
    h=account(client);other=account(client,'other@example.test');linked(client,h)
    tool_calls=[]
    def tool(token,name,arguments):
        tool_calls.append((name,arguments))
        if name=='search_restaurants':return {'restaurants':[{'id':'100','name':'Synthetic venue','distanceKm':1.5,'availabilityStatus':'OPEN'},{'id':'101','name':'Closed','distanceKm':1,'availabilityStatus':'CLOSED'},{'id':'102','name':'Too far','distanceKm':3,'availabilityStatus':'OPEN'},{'id':'103','name':'Unknown distance','availabilityStatus':'OPEN'}]}
        return {'items':[{'restaurant_id':'100','name':'Synthetic noodles','price':199.50,'inStock':1,'hasVariants':False,'hasAddons':False},{'restaurant_id':'100','name':'Variant dish','price':100,'inStock':1,'hasVariants':True},{'restaurant_id':'101','name':'Wrong branch','price':10,'inStock':1}]}
    monkeypatch.setattr(platforms,'read_tool',tool)
    with Session() as db:before=[db.scalar(select(func.count()).select_from(t)) for t in (MenuItem,Search,IngestionLog)]
    result=client.post('/platforms/swiggy/search',headers=h,json={'query':'Hakka noodles under 300 within 2 km','area':'Bandra'});assert result.status_code==200,result.text
    venues=result.json()['restaurants'];assert len(venues)==1 and venues[0]['id']=='100';assert len(tool_calls)==1
    selection=venues[0]['selection']
    assert client.post('/platforms/swiggy/menu',headers=other,json={'selection':selection,'query':'noodles'}).status_code==400
    result=client.post('/platforms/swiggy/menu',headers=h,json={'selection':selection,'query':'noodles'});assert result.status_code==200,result.text
    items=result.json()['items'];assert len(items)==2 and items[0]['price_paise']==19950 and items[0]['within_budget'] is True
    assert items[1]['within_budget'] is None
    assert tool_calls[-1][1]['restaurantIdOfAddedItem']=='100'
    monkeypatch.setenv('SWIGGY_MCP_PRICE_UNIT','unknown')
    result=client.post('/platforms/swiggy/menu',headers=h,json={'selection':selection,'query':'noodles'});assert all(x['price_paise'] is None and x['within_budget'] is None for x in result.json()['items'])
    with Session() as db:assert [db.scalar(select(func.count()).select_from(t)) for t in (MenuItem,Search,IngestionLog)]==before

def test_expired_token_rotation_and_read_only_reauth(client,configured,provider,monkeypatch):
    h=account(client);linked(client,h)
    with Session() as db:
        row=db.scalar(select(ProviderConnection));row.expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();db.commit()
    calls=[]
    def tool(token,name,args):
        calls.append(name)
        if len(calls)==1:raise HTTPException(401,'Revoked')
        return {'restaurants':[]}
    monkeypatch.setattr(platforms,'read_tool',tool)
    result=client.post('/platforms/swiggy/search',headers=h,json={'query':'Chinese'});assert result.status_code==200,result.text
    refreshes=[p for path,p,t in provider if path=='/auth/token' and p['grant_type']=='refresh_token'];assert len(refreshes)==2
    assert calls==['search_restaurants','search_restaurants']

def test_mcp_json_sse_allowed_tools_and_429(client,configured,monkeypatch):
    payload={'jsonrpc':'2.0','id':2,'result':{'structuredContent':{'success':True,'data':{'restaurants':[]}}}}
    body=': heartbeat\n\nevent: message\ndata: '+json.dumps(payload)+'\n\n'
    assert platforms.rpc_result(body,2,'text/event-stream')==payload['result']
    with pytest.raises(HTTPException) as bad:platforms.read_tool('private','place_food_order',{})
    assert bad.value.status_code==400
    requests=[]
    def transport(request):
        data=json.loads(request.content);requests.append(data)
        if data['method']=='initialize':return httpx.Response(200,json={'jsonrpc':'2.0','id':1,'result':{'protocolVersion':'2025-03-26'}},headers={'mcp-session-id':'synthetic-session'})
        if data['method']=='notifications/initialized':return httpx.Response(202)
        assert request.headers['mcp-session-id']=='synthetic-session'
        return httpx.Response(200,text=body,headers={'content-type':'text/event-stream'})
    real=httpx.Client
    monkeypatch.setattr(platforms.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(transport),**kwargs))
    assert platforms.read_tool('private','search_restaurants',{'query':'Chinese'})=={'restaurants':[]}
    assert [r['method'] for r in requests]==['initialize','notifications/initialized','tools/call']
    monkeypatch.setattr(platforms.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(lambda r:httpx.Response(429,headers={'Retry-After':'45'})),**kwargs))
    with pytest.raises(HTTPException) as busy:platforms.read_tool('private','search_restaurants',{})
    assert busy.value.status_code==429 and busy.value.headers['Retry-After']=='45'

def test_token_retention_purge_and_private_error_headers(client,configured,provider):
    h=account(client);linked(client,h)
    with Session() as db:
        row=db.scalar(select(ProviderConnection));row.retain_until=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();db.commit()
    assert not client.get('/platforms/status',headers=h).json()['swiggy']['connected']
    assert client.post('/platforms/swiggy/search',headers=h,json={'query':'Chinese'}).status_code==401
    with Session() as db:assert db.scalar(select(func.count()).select_from(ProviderConnection))==0
    denied=client.get('/platforms/swiggy/callback?state=invalid&code=synthetic-secret',headers=h)
    assert denied.status_code==400 and denied.headers['cache-control']=='no-store' and denied.headers['referrer-policy']=='no-referrer'
    assert 'synthetic-secret' not in denied.text

def test_zomato_pkce_provider_binding_and_schema_capture(client,configured,provider,monkeypatch):
    from app import zomato
    monkeypatch.setenv('ZOMATO_MCP_ENABLED','true')
    def request(path,payload):
        return {'client_id':'zomato-synthetic-client'} if path=='/register' else {'access_token':'zomato-private','refresh_token':'zomato-refresh','expires_in':3600}
    monkeypatch.setattr(zomato,'request_token',request)
    monkeypatch.setattr(zomato,'read_tool',lambda token,name,args,**kwargs:{'tools':[{'name':'synthetic_read_tool','inputSchema':{'type':'object'},'annotations':{'readOnlyHint':True}}]})
    h=account(client);start=client.post('/platforms/zomato/connect',headers=h);assert start.status_code==200,start.text
    url=start.json()['authorization_url'];assert url.startswith('https://mcp-server.zomato.com/authorize?')
    state=parse_qs(urlsplit(url).query)['state'][0]
    assert client.get('/platforms/swiggy/callback',params={'code':'synthetic','state':state},headers=h).status_code==400
    result=client.get('/platforms/zomato/callback',params={'code':'synthetic','state':state},headers=h,follow_redirects=False);assert result.status_code==303,result.text
    status=client.get('/platforms/status',headers=h).json();assert status['zomato']['connected'] and status['zomato']['can_connect'] and not status['zomato']['available']
    assert not status['swiggy']['connected']
    with Session() as db:
        row=db.scalar(select(ProviderConnection));assert row.provider=='zomato' and 'zomato-private' not in row.encrypted_tokens
        assert json.loads(row.tool_manifest)[0]['name']=='synthetic_read_tool'
    assert client.delete('/platforms/zomato',headers=h).json()['disconnected']
    assert not client.get('/platforms/status',headers=h).json()['zomato']['connected']

def test_oauth_authorization_codes_are_redacted_from_access_logs():
    import logging
    from app.main import PrivateRequestQueries
    record=logging.LogRecord('uvicorn.access',logging.INFO,'',0,'%s - "%s %s HTTP/%s" %d',('127.0.0.1','GET','/platforms/swiggy/callback?code=private-code&state=private-state','1.1',303),None)
    assert PrivateRequestQueries().filter(record)
    assert '/platforms/swiggy/callback' in record.getMessage()
    assert 'private-code' not in record.getMessage() and 'private-state' not in record.getMessage()

def test_mcp_returns_on_matching_sse_event_without_waiting_for_stream_close(monkeypatch):
    class KeptOpen(httpx.SyncByteStream):
        def __iter__(self):
            yield b': heartbeat\n\n'
            yield b'data: {"jsonrpc":"2.0","id":2,"result":{"structuredContent":{"success":true,"data":{"restaurants":[]}}}}\n\n'
            raise AssertionError('Must close after the matching response, not wait for SSE EOF')
    def transport(request):
        data=json.loads(request.content)
        if data['method']=='initialize':return httpx.Response(200,json={'jsonrpc':'2.0','id':1,'result':{'protocolVersion':'2025-03-26'}})
        if data['method']=='notifications/initialized':return httpx.Response(202)
        return httpx.Response(200,stream=KeptOpen(),headers={'content-type':'text/event-stream'})
    real=httpx.Client
    monkeypatch.setattr(platforms.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(transport),**kwargs))
    assert platforms.read_tool('synthetic-token','search_restaurants',{'query':'Chinese'})=={'restaurants':[]}
