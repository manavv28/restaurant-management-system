"""Observed production regressions: dish identity, origin and coverage evidence."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from test_api import client,account,restaurant
from app.database import Session,Restaurant,MenuItem,CatalogSource,CatalogJob,Search
from app.catalog_worker import schedule


def test_pizza_snacks_cannot_hide_a_real_pizza_at_same_restaurant(client):
    owner=account(client,'pizza-audit@example.test','owner');rid=restaurant(client,owner)
    for name,price in [('BK Veg Pizza Puff.',6500),('BK Veg Pizza Puff+Coke.',16400),('Veg Pizza McPuff',6900),('Extra Cheese In Pizza',5000),('Pizza Bread 125gm',3000),('Pizza Stick (6Pcs)',12000),('Pizza Samosa [250 grams]',10000),('Cheesy Pizza Fingers',12000),('Pizza Pocket',7000),('Pizza Sandwich',8000),('Margherita Pizza (Regular)',18000)]:
        assert client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':name,'cuisine':'Italian','price_paise':price}).status_code==200
    rows=client.post('/search',json={'query':'pizza under 200','include_samples':False}).json()['results']
    assert len(rows)==1 and rows[0]['dish']['name']=='Margherita Pizza (Regular)'
    snack=client.post('/search',json={'query':'pizza puff under 200','include_samples':False}).json()['results']
    assert len(snack)==1 and snack[0]['dish']['name']=='BK Veg Pizza Puff.'
    with Session() as db:
        db.scalar(select(MenuItem).where(MenuItem.restaurant_id==rid,MenuItem.name=='Margherita Pizza (Regular)')).available=False;db.commit()
    assert client.post('/search',json={'query':'pizza under 200','include_samples':False}).json()['results']==[]


def test_known_dish_does_not_depend_on_incomplete_restaurant_cuisine(client):
    owner=account(client,'cuisine-audit@example.test','owner');rid=restaurant(client,owner)
    client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':'Veg. Hakka Noodles','cuisine':'Unspecified','price_paise':11000})
    with Session() as db:db.get(Restaurant,rid).cuisine='Unspecified';db.commit()
    query={'include_samples':False}
    short=client.post('/search',json={**query,'query':'hakka noodles under 300 within 2 km'}).json()
    long=client.post('/search',json={**query,'query':'Chinese haka noodles for 300 within 2 km'}).json()
    assert [r['restaurant']['id'] for r in short['results']]==[r['restaurant']['id'] for r in long['results']]==[rid]


def test_generic_cuisine_does_not_recommend_bottled_water(client):
    owner=account(client,'meal-audit@example.test','owner');rid=restaurant(client,owner)
    for name,price in [('Bisleri (500 ml)',1000),('Veg Fried Rice',18000)]:
        client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':name,'cuisine':'Chinese','price_paise':price})
    rows=client.post('/search',json={'query':'Chinese','include_samples':False}).json()['results']
    assert rows[0]['dish']['name']=='Veg Fried Rice'


def test_beverages_require_an_explicit_dish_request(client):
    from app.agents import parse_local
    assert parse_local('steamed rice under 300').dish is None
    assert parse_local('coffee under 100').dish=='coffee'
    rows=client.post('/search',json={'query':'South Indian under 200 within 10 km'}).json()['results']
    assert rows and all('coffee' not in row['dish']['name'].casefold() for row in rows)
    drinks=client.post('/search',json={'query':'coffee under 100 within 10 km'}).json()['results']
    assert drinks and drinks[0]['dish']['name']=='Filter coffee'


def test_search_origin_identifies_gps_and_explicit_area(client):
    gps={'latitude':19.0596,'longitude':72.8295}
    assert client.post('/search',json={'query':'noodles',**gps}).json()['search_origin']['kind']=='gps'
    area=client.post('/search',json={'query':'noodles in Andheri',**gps}).json()['search_origin']
    assert area['kind']=='area_centre' and area['label']=='Andheri area centre'


def test_locality_and_contact_coverage_excludes_samples(client):
    owner=account(client,'coverage-audit@example.test','owner');rid=restaurant(client,owner)
    with Session() as db:db.get(Restaurant,rid).phone='9876543210';db.commit()
    data=client.get('/catalog/coverage').json()
    assert data['phone_types']=={'mobile':1,'landline':0,'unclassified':0}
    bandra=next(row for row in data['areas'] if row['area']=='Bandra')
    assert bandra['listings']==1 and bandra['priced_restaurants']==0 and bandra['missing_menu_prices']==1
    assert 'not a complete Mumbai census' in data['locality_notice']


def test_demand_prioritises_collection_without_bypassing_cooldown(client):
    with Session() as db:
        db.add_all([CatalogSource(kind='osm',area='Bandra',url='https://example.test/1',permission_note='fixture'),
                    CatalogSource(kind='osm',area='Andheri',url='https://example.test/2',permission_note='fixture')])
        db.add(Search(query='pizza',area='Andheri',budget=300,results=0,trace='[]'));db.commit()
        assert schedule(db)==2
        first=db.scalar(select(CatalogJob).order_by(CatalogJob.id))
        assert db.get(CatalogSource,first.source_id).area=='Andheri'
        assert schedule(db)==0


def test_dead_menu_link_does_not_block_a_later_valid_link(client,monkeypatch):
    import asyncio,json
    import app.catalog_worker as worker
    from test_catalog import source
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menu.example.test')
    with Session() as db:
        entry=source(db);entry.url='https://menu.example.test/';db.add(CatalogJob(source_id=entry.id));db.commit()
    async def fetch(entry):
        if entry.url.endswith('/broken-menu'):raise ValueError('Redirects must be approved as a separate source URL')
        if entry.url.endswith('/food-menu'):
            return '<script type="application/ld+json">'+json.dumps({'@type':'MenuItem','name':'Hakka noodles','offers':{'price':'250','priceCurrency':'INR'}})+'</script>'
        return '<a href="/broken-menu">Old menu</a><a href="/food-menu">Food menu</a>'
    monkeypatch.setattr(worker,'fetch_menu',fetch)
    result=asyncio.run(worker.run_one())
    assert result['state']=='succeeded'
    assert any(step['tool']=='menu_link_unavailable' for step in result['trace'])
    assert any(step['tool']=='approved_menu_link' for step in result['trace'])
