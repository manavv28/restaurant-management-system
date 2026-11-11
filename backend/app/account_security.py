"""Persistent throttling, one-use recovery tokens and TLS SMTP delivery."""
import hashlib,hmac,os,secrets,ssl,smtplib,time
from datetime import datetime,timedelta,timezone
from email.message import EmailMessage
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy import select,delete
from .database import Session,User,SecurityToken,RateLimit,AuthSession,now
from .security import db_session,current_user,passwords,SECRET
from .schemas import EmailInput,TokenInput,ResetInput

router=APIRouter(tags=['Account security'])

def throttle(db,scope,identity,limit=8,seconds=300):
    bucket=int(time.time())//seconds
    key=hmac.new(SECRET.encode(),f'{scope}:{identity}:{bucket}'.encode(),hashlib.sha256).hexdigest()
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert=pg_insert if db.bind.dialect.name=='postgresql' else sqlite_insert
    query=insert(RateLimit).values(key=key,attempts=1,expires_at=(datetime.now(timezone.utc)+timedelta(seconds=seconds*2)).isoformat())
    query=query.on_conflict_do_update(index_elements=['key'],set_={'attempts':RateLimit.attempts+1}).returning(RateLimit.attempts)
    count=db.scalar(query);db.commit()
    if count>limit:raise HTTPException(429,'Too many attempts. Please try again later.',headers={'Retry-After':str(seconds)})

def throttle_auth(db,request,email):
    # The socket address cannot be spoofed with an untrusted X-Forwarded-For header.
    # Coarse connection limit complements the tighter per-account limit behind proxies.
    throttle(db,'auth-connection',request.client.host if request.client else 'unknown',200)
    throttle(db,'auth-account',email.strip().lower())

def mail_enabled():
    base=os.getenv('PUBLIC_APP_URL','')
    return bool(os.getenv('SMTP_HOST') and os.getenv('EMAIL_FROM')
                and urlsplit(base).scheme=='https'
                and (not os.getenv('SMTP_USER') or os.getenv('SMTP_PASSWORD')))

def send_security_email(email,purpose,token):
    if not mail_enabled():raise RuntimeError('Email delivery is not configured')
    base=os.environ['PUBLIC_APP_URL'].rstrip('/')
    if urlsplit(base).scheme!='https':raise RuntimeError('Public email links require HTTPS')
    message=EmailMessage();message['From']=os.environ['EMAIL_FROM'];message['To']=email
    message['Subject']='Verify your BiteAI email' if purpose=='verify' else 'Reset your BiteAI password'
    message.set_content(f'Open this link to {"verify your email" if purpose=="verify" else "reset your password"}:\n{base}/#{purpose}={token}\n\nThis link expires in 20 minutes. Ignore it if you did not request it.')
    port=int(os.getenv('SMTP_PORT','465'))
    with smtplib.SMTP_SSL(os.environ['SMTP_HOST'],port,timeout=15,context=ssl.create_default_context()) as smtp:
        if os.getenv('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ.get('SMTP_PASSWORD',''))
        smtp.send_message(message)

def issue(db,user,purpose):
    # Lock the user before replacing existing tokens to serialize concurrent requests.
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    db.execute(delete(SecurityToken).where(SecurityToken.user_id==user.id,SecurityToken.purpose==purpose))
    value=secrets.token_urlsafe(32);digest=hashlib.sha256(value.encode()).hexdigest()
    db.add(SecurityToken(id=digest,user_id=user.id,purpose=purpose,expires_at=(datetime.now(timezone.utc)+timedelta(minutes=20)).isoformat()));db.commit()
    try:send_security_email(user.email,purpose,value)
    except Exception:
        db.execute(delete(SecurityToken).where(SecurityToken.id==digest));db.commit()
        # Do not log addresses, SMTP responses or raw bearer tokens.
        raise HTTPException(503,'Email delivery unavailable. Please try again later.') from None

def consume(db,value,purpose):
    digest=hashlib.sha256(value.encode()).hexdigest()
    row=db.scalar(select(SecurityToken).where(SecurityToken.id==digest,SecurityToken.purpose==purpose).with_for_update())
    if not row or row.expires_at<=now():raise HTTPException(400,'Link is invalid or expired')
    user=db.scalar(select(User).where(User.id==row.user_id).with_for_update())
    if not user:raise HTTPException(400,'Link is invalid or expired')
    db.delete(row)
    return user

@router.get('/auth/email-availability')
def email_availability():return {'enabled':mail_enabled()}

@router.post('/auth/forgot-password',status_code=202)
def forgot(body:EmailInput,request:Request,db=Depends(db_session)):
    throttle_auth(db,request,body.email)
    if not mail_enabled():raise HTTPException(503,'Email delivery is not configured')
    user=db.scalar(select(User).where(User.email==body.email.strip().lower()))
    if user:
        try:issue(db,user,'reset')
        except HTTPException:pass # Same public response for known and unknown addresses.
    return {'message':'If an account exists, a password-reset email will be sent.'}

@router.post('/auth/reset-password')
def reset(body:ResetInput,request:Request,db=Depends(db_session)):
    throttle(db,'recovery-token',request.client.host if request.client else 'unknown',30)
    user=consume(db,body.token,'reset');user.password_hash=passwords.hash(body.password)
    db.execute(delete(AuthSession).where(AuthSession.user_id==user.id))
    db.execute(delete(SecurityToken).where(SecurityToken.user_id==user.id,SecurityToken.purpose=='reset'))
    db.commit();return {'message':'Password updated. Sign in again on your devices.'}

@router.post('/me/request-verification')
def request_verification(user=Depends(current_user),db=Depends(db_session)):
    throttle(db,'verification',str(user.id),3)
    if not user.email_verified:issue(db,user,'verify')
    return {'message':'Check your email for the verification link.'}

@router.post('/auth/verify-email')
def verify(body:TokenInput,request:Request,db=Depends(db_session)):
    throttle(db,'verify-token',request.client.host if request.client else 'unknown',30)
    user=consume(db,body.token,'verify');user.email_verified=True;db.commit()
    return {'message':'Email verified.'}
