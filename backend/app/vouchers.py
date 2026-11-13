"""Deal vouchers: signed test-mode capture first; only the owning restaurant can redeem."""
import io,uuid,json
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import select,delete
from .database import DealVoucher,PaymentOrder,Redemption,Restaurant,Transaction,Campaign,now
from .security import SECRET,current_user,owner,db_session
router=APIRouter(tags=['Deal vouchers'])

def voucher_token(row):
    return jwt.encode({'aud':'biteai-voucher','vid':row.id,'exp':datetime.fromisoformat(row.expires_at)},SECRET,algorithm='HS256')

def details(db,row):
    order=db.get(PaymentOrder,row.payment_order_id);redemption=db.get(Redemption,row.redemption_id);restaurant=db.get(Restaurant,order.restaurant_id)
    return {'id':row.id,'restaurant_name':restaurant.name,'state':row.state,'expires_at':row.expires_at,'redeemed_at':row.redeemed_at,'amount_paise':order.amount_paise,'discount_paise':redemption.discount_paise,'test_mode':order.test_mode,
            'code':voucher_token(row) if row.state=='issued' else None,'notice':'Test-mode deal voucher; no real money moved.' if order.test_mode else 'Provider-verified deal voucher'}

@router.get('/me/vouchers')
def mine(user=Depends(current_user),db=Depends(db_session)):
    rows=db.scalars(select(DealVoucher).join(PaymentOrder).where(PaymentOrder.user_id==user.id).order_by(DealVoucher.expires_at.desc()).limit(50)).all()
    return [details(db,row) for row in rows]

@router.get('/me/vouchers/{vid}/qr')
def qr(vid:str,user=Depends(current_user),db=Depends(db_session)):
    row=db.scalar(select(DealVoucher).join(PaymentOrder).where(DealVoucher.id==vid,PaymentOrder.user_id==user.id))
    if not row or row.state!='issued' or row.expires_at<=now():raise HTTPException(404,'Active voucher not found')
    import qrcode,qrcode.image.svg
    image=qrcode.make(voucher_token(row),image_factory=qrcode.image.svg.SvgPathImage);buffer=io.BytesIO();image.save(buffer)
    return Response(buffer.getvalue(),media_type='image/svg+xml',headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'"})

class Scan(BaseModel):
    code:str=Field(min_length=20,max_length=2000)
@router.post('/portal/vouchers/redeem')
def redeem(body:Scan,user=Depends(owner),db=Depends(db_session)):
    try:claims=jwt.decode(body.code.strip(),SECRET,algorithms=['HS256'],audience='biteai-voucher',options={'require':['exp','vid']})
    except jwt.PyJWTError:raise HTTPException(400,'Voucher code is invalid or expired') from None
    row=db.scalar(select(DealVoucher).where(DealVoucher.id==claims['vid']).with_for_update())
    if not row:raise HTTPException(404,'Voucher not found')
    order=db.get(PaymentOrder,row.payment_order_id);restaurant=db.get(Restaurant,order.restaurant_id)
    if restaurant.owner_id!=user.id:raise HTTPException(403,'This voucher belongs to another restaurant')
    transaction=db.scalar(select(Transaction).where(Transaction.provider_order_id==order.provider_order_id))
    if not transaction or transaction.disputed or transaction.refunded_paise or order.state!='captured':raise HTTPException(409,'Payment is not eligible for voucher redemption')
    if row.state!='issued' or row.expires_at<=now():raise HTTPException(409,'Voucher is not active or has already been redeemed')
    row.state='redeemed';row.redeemed_at=now();db.commit()
    return details(db,row)
