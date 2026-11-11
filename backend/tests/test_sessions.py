import hashlib
from datetime import datetime,timedelta,timezone
import jwt
from test_api import client,account
from app.database import Session,AuthSession
from app.security import COOKIE,SECRET

BROWSER={'x-biteai-client':'browser'}

def browser_login(client):
    return client.post('/auth/register',headers=BROWSER,json={'name':'Cookie user','email':'cookie@example.test','password':'secure-cookie-password'})

def test_cookie_session_csrf_and_revocation(client):
    response=browser_login(client)
    assert response.status_code==200 and 'token' not in response.json()
    cookie=response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert response.headers['cache-control']=='no-store'
    value=client.cookies.get(COOKIE)
    assert client.get('/me').status_code==200
    assert client.put('/me/consent',json={'consent':True}).status_code==403
    assert client.put('/me/consent',headers={**BROWSER,'sec-fetch-site':'cross-site'},json={'consent':True}).status_code==403
    assert client.put('/me/consent',headers=BROWSER,json={'consent':True}).status_code==200
    assert client.post('/auth/logout',headers=BROWSER).status_code==200
    assert client.get('/me').status_code==401
    assert client.get('/me',headers={'authorization':'Bearer '+value}).status_code==401


def test_expired_database_session_and_legacy_token_rejected(client):
    browser_login(client)
    value=client.cookies.get(COOKIE)
    sid=jwt.decode(value,SECRET,algorithms=['HS256'])['sid']
    with Session() as db:
        session=db.get(AuthSession,hashlib.sha256(sid.encode()).hexdigest())
        session.expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();db.commit()
    assert client.get('/me').status_code==401
    legacy=jwt.encode({'sub':'1','exp':datetime.now(timezone.utc)+timedelta(hours=1)},SECRET,algorithm='HS256')
    assert client.get('/me',headers={'authorization':'Bearer '+legacy}).status_code==401


def test_production_cookie_is_secure(client,monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    assert 'Secure' in browser_login(client).headers['set-cookie']


def test_browser_header_cannot_be_used_from_untrusted_cors_origin(client):
    response=client.options('/auth/login',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'x-biteai-client,content-type'})
    assert response.status_code==400
