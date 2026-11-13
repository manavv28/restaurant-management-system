"""Catalog completeness by assigned locality; never a census of Mumbai businesses."""
from sqlalchemy import select,func
from .database import Restaurant,MenuItem,MenuEvidence,now
from .contact_enrichment import business_phone


def locality_coverage(db):
    priced=select(MenuItem.restaurant_id).join(MenuEvidence,MenuEvidence.menu_item_id==MenuItem.id).where(
        MenuItem.available.is_(True),MenuEvidence.active.is_(True),MenuEvidence.expires_at>now()).distinct().subquery()
    rows=db.execute(select(Restaurant.area,func.count(Restaurant.id),func.count(priced.c.restaurant_id)).outerjoin(
        priced,priced.c.restaurant_id==Restaurant.id).where(Restaurant.sample.is_(False)).group_by(Restaurant.area)).all()
    areas=[{'area':area,'listings':total,'priced_restaurants':count,'missing_menu_prices':total-count,
            'menu_coverage_percent':round(100*count/total,1) if total else 0} for area,total,count in rows]
    contacts={'mobile':0,'landline':0,'unclassified':0}
    for phone in db.scalars(select(Restaurant.phone).where(Restaurant.sample.is_(False),Restaurant.phone!='')):
        normalized=business_phone(phone)
        contacts['mobile' if normalized and normalized[3] in '6789' else 'landline' if normalized else 'unclassified']+=1
    return {'areas':sorted(areas,key=lambda row:row['area']), 'phone_types':contacts,
            'phone_type_notice':'Number-format classification only; public business contacts are not verified as active or WhatsApp-enabled.',
            'locality_notice':'Coverage is within assigned catalog localities, not a complete Mumbai census or a GPS radius.'}
