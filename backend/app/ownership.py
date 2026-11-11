"""Prove control of a restaurant website using a DNS TXT challenge."""
import hashlib,hmac,ipaddress,secrets
from urllib.parse import urlsplit
from datetime import datetime,timedelta,timezone
import httpx
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .database import Restaurant,OwnershipProof,now
from .security import owner,db_session
from .account_security import throttle
router=APIRouter(prefix='/portal/restaurants',tags=['Ownership'])

def owned(db,rid,user):
    restaurant=db.get(Restaurant,rid)
    if not restaurant:raise HTTPException(404,'Restaurant not found')
    if restaurant.owner_id!=user.id:raise HTTPException(403,'You do not own this restaurant')
    return restaurant

def hostname(website):
    host=urlsplit(website).hostname or ''
    if not host or '.' not in host or urlsplit(website).scheme!='https':raise HTTPException(422,'Set your restaurant HTTPS website first')
    try:ipaddress.ip_address(host)
    except ValueError:return host.encode('idna').decode('ascii')
    raise HTTPException(422,'A public domain name is required')

@router.post('/{rid}/ownership-challenge')
def challenge(rid:int,user=Depends(owner),db=Depends(db_session)):
    throttle(db,'ownership-challenge',str(user.id),5)
    restaurant=owned(db,rid,user);host=hostname(restaurant.website)
    if restaurant.sample:raise HTTPException(422,'Cannot verify a fictional restaurant')
    value=secrets.token_urlsafe(32)
    proof=db.get(OwnershipProof,rid)
    if not proof:proof=OwnershipProof(restaurant_id=rid);db.add(proof)
    proof.hostname=host;proof.token_hash=hashlib.sha256(value.encode()).hexdigest()
    proof.expires_at=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat();proof.verified_at=None
    db.commit()
    return {'record_name':'_biteai.'+host,'record_type':'TXT','record_value':'biteai-verification='+value,'expires_at':proof.expires_at}

@router.post('/{rid}/verify-ownership')
async def verify(rid:int,user=Depends(owner),db=Depends(db_session)):
    throttle(db,'ownership-verify',str(user.id),10)
    restaurant=owned(db,rid,user);host=hostname(restaurant.website)
    proof=db.get(OwnershipProof,rid)
    if not proof or proof.hostname!=host or proof.expires_at<=now():raise HTTPException(400,'Create a new verification challenge')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response=await client.get('https://dns.google/resolve',params={'name':'_biteai.'+host,'type':'TXT'})
            response.raise_for_status();data=response.json()
        matched=False
        for record in data.get('Answer',[]):
            if record.get('type')!=16:continue
            value=record.get('data','').strip('"')
            if value.startswith('biteai-verification=') and hmac.compare_digest(hashlib.sha256(value.split('=',1)[1].encode()).hexdigest(),proof.token_hash):matched=True
    except (httpx.HTTPError,ValueError,TypeError):raise HTTPException(502,'DNS lookup unavailable') from None
    if not matched:raise HTTPException(409,'Verification TXT record not found yet')
    # Refresh under lock so a superseded challenge cannot verify a changed domain.
    original=proof.token_hash
    restaurant=db.scalar(select(Restaurant).where(Restaurant.id==rid).with_for_update().execution_options(populate_existing=True))
    proof=db.scalar(select(OwnershipProof).where(OwnershipProof.restaurant_id==rid).with_for_update().execution_options(populate_existing=True))
    if not proof or proof.expires_at<=now() or proof.token_hash!=original or hostname(restaurant.website)!=host:raise HTTPException(409,'Website or challenge changed; try again')
    restaurant.ownership_verified=True;proof.verified_at=now();db.commit()
    return {'verified':True,'notice':'Website control verified; this does not certify food quality or legal merchant identity.'}
