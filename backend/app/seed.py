from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from .database import Restaurant, MenuItem, Campaign

def seed(db):
    if db.scalar(select(Restaurant.id).where(Restaurant.sample.is_(True)).limit(1)): return
    records = [
        ('Sample · Wok & Wonder','Bandra',19.061,72.831,'Chinese',[('Hakka noodles',240),('Chilli garlic noodles',280),('Vegetable fried rice',220)]),
        ('Sample · Little Napoli','Bandra',19.055,72.827,'Italian',[('Margherita pizza',390),('Pesto pasta',320)]),
        ('Sample · The Masala Room','Andheri',19.121,72.847,'Indian',[('Vegetable biryani',260),('Paneer tikka',290)]),
        ('Sample · Dosa District','Dadar',19.019,72.849,'South Indian',[('Masala dosa',140),('Filter coffee',80)]),
        ('Sample · Green Bowl','Powai',19.118,72.905,'Japanese',[('Vegetable sushi',420),('Miso noodles',280)]),
        ('Sample · Harbour Table','Colaba',18.908,72.816,'Indian',[('Paneer tikka',310),('Vegetable biryani',280)]),
    ]
    for name, area, lat, lng, cuisine, menu in records:
        r = Restaurant(name=name,address='Fictional demonstration location, '+area+', Mumbai',area=area,latitude=lat,longitude=lng,cuisine=cuisine,sample=True,source='Fictional sample data — not a real business')
        db.add(r); db.flush()
        for dish,price in menu:
            db.add(MenuItem(restaurant_id=r.id,name=dish,cuisine=cuisine,price_paise=price*100,source='Fictional sample menu — not a verified price'))
        db.add(Campaign(restaurant_id=r.id,title='Sample discovery reward',percent=5,min_searches=5,max_discount_paise=10000,min_order_paise=20000,
            ends_at=(datetime.now(timezone.utc)+timedelta(days=90)).isoformat()))
    db.commit()
