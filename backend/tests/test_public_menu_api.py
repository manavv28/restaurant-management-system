"""Synthetic API fixtures; no external provider is contacted by tests."""
import copy,json,hashlib
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy import select,func,event
from test_api import client
from app.database import Session,Restaurant,MenuItem,MenuEvidence,CatalogSource,User,IngestionLog,engine
from app.public_menu_api import prepare_snapshot,persist_snapshots,provider_id

def snapshot():
    return {'api_url':'https://indiarestros.com/api/v1/restaurants/IRR-0000000001/menu',
            'retrieved_at':datetime.now(timezone.utc).isoformat(),'content_hash':hashlib.sha256(b'Synthetic fixture').hexdigest(),
            'identity':{'canonical_source_id':'osm:node:fixture','match_method':'synthetic'},
            'listing':{'id':'IRR-0000000001','name':'Fixture Kitchen','cuisines':['chinese']},
            'menu':{'restaurant':'IRR-0000000001','name':'Fixture Kitchen','url':'https://indiarestros.com/r/fixture-kitchen/menu',
                    'source':'fixture-publisher','source_url':'https://publisher.example.test/fixture-kitchen/order','updated':(datetime.now(timezone.utc)-timedelta(days=30)).isoformat(),
                    'sections':[{'name':'Noodles','items':[{'name':'Fixture noodles','price':199.50,'desc':'Copyrighted description is not imported'},{'name':'Fixture rice','price':149}]}]}}

def venue(db):
    r=Restaurant(name='Fixture Kitchen',address='Synthetic address',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese',sample=False,source_id='osm:node:fixture')
    db.add(r);db.commit();return r

def pg():
    if engine.dialect.name!='postgresql':pytest.skip('PostgreSQL required for atomic public API imports')

def test_exact_price_facts_retain_dates_and_omit_descriptions():
    raw=snapshot();raw['menu']['sections'][0]['items'] += [{'name':'Ambiguous','price':100},{'name':'Ambiguous','price':150},{'name':'Invalid','price':'120-150'},{'name':'Free addon','price':0}]
    prepared=prepare_snapshot(raw)
    assert len(prepared['items'])==2 and prepared['items'][0]['price_paise']==19950
    assert prepared['metadata']['provider_updated_at']==raw['menu']['updated']
    assert prepared['metadata']['price_context']=='delivery listing'
    assert prepared['metadata']['cuisines']==['chinese']
    assert 'Copyrighted' not in json.dumps(prepared)
    assert prepared['rejected_items']==4
    bad=copy.deepcopy(raw);bad['menu']['restaurant']='IRR-0000000002'
    with pytest.raises(ValueError,match='identity'):prepare_snapshot(bad)
    with pytest.raises(ValueError):provider_id('https://evil.example.test/menu')

def test_publication_replay_price_change_withdrawal_and_original_date(client):
    pg()
    with Session() as db:
        r=venue(db);prepared=prepare_snapshot(snapshot())
        result=persist_snapshots(db,[prepared]);db.commit()
        assert result['saved_items']==2 and result['evidence_items']==2
        persist_snapshots(db,[prepared]);db.commit()
        assert db.scalar(select(func.count()).select_from(MenuItem).where(MenuItem.restaurant_id==r.id))==2
        raw=snapshot();raw['menu']['sections'][0]['items']=[{'name':'Fixture noodles','price':190.50}]
        result=persist_snapshots(db,[prepare_snapshot(raw)]);db.commit()
        assert result['saved_items']==1 and result['withdrawn_items']==1
        rice=db.scalar(select(MenuItem).where(MenuItem.restaurant_id==r.id,MenuItem.name=='Fixture rice'))
        assert not rice.available and not db.get(MenuEvidence,rice.id).active
        audit=json.loads(db.scalars(select(IngestionLog).where(IngestionLog.restaurant_id==r.id).order_by(IngestionLog.id.desc())).first().trace)
        assert audit['price_changes'][0]['before_paise']==19950 and audit['price_changes'][0]['after_paise']==19050
    details=client.get(f'/restaurants/{r.id}').json()['menu']
    dish=next(d for d in details if d['name']=='Fixture noodles')
    assert dish['price_is_reference'] and (datetime.now(timezone.utc)-timedelta(days=30)).date().isoformat() in dish['price_status']
    assert 'fresh' not in dish['price_status'].lower() and dish['price_paise']==19050
    assert 'source_key' not in dish

def test_owned_restaurant_and_owner_menu_are_preserved(client):
    pg()
    with Session() as db:
        r=venue(db)
        original=MenuItem(restaurant_id=r.id,name='Fixture noodles',cuisine='Chinese',price_paise=8800,source='Owner supplied')
        db.add(original);db.commit();mid=original.id
        result=persist_snapshots(db,[prepare_snapshot(snapshot())]);db.commit()
        assert result['saved_items']==1 and db.get(MenuItem,mid).price_paise==8800
        assert db.get(MenuEvidence,mid) is None
        owner=User(email='fixture-owner@example.test',name='Synthetic owner',password_hash='unused-fixture',role='owner')
        db.add(owner);db.flush();r.owner_id=owner.id;db.commit()
        result=persist_snapshots(db,[prepare_snapshot(snapshot())]);db.commit()
        assert result['eligible_restaurants']==0 and result['saved_items']==0

def test_paused_feed_does_not_reactivate_or_refresh_prices(client):
    pg()
    with Session() as db:
        r=venue(db);persist_snapshots(db,[prepare_snapshot(snapshot())]);db.commit()
        feed=db.scalar(select(CatalogSource).where(CatalogSource.restaurant_id==r.id));feed.enabled=False;db.commit()
        changed=snapshot();changed['menu']['sections'][0]['items'][0]['price']=99
        assert persist_snapshots(db,[prepare_snapshot(changed)])['saved_items']==0;db.commit()
        assert not feed.enabled
        item=db.scalar(select(MenuItem).where(MenuItem.restaurant_id==r.id,MenuItem.name=='Fixture noodles'))
        assert item.price_paise==19950

def test_large_menu_search_hydrates_only_bounded_recommendations(client):
    from sqlalchemy.orm import Session as OrmSession
    with Session() as db:
        for n in range(40):
            r=Restaurant(name=f'Synthetic venue {n}',address='Fixture only',area='Bandra',latitude=19.0596+n*.00001,longitude=72.8295,cuisine='Chinese',sample=False)
            db.add(r);db.flush()
            db.add_all([MenuItem(restaurant_id=r.id,name=f'Fixture Hakka noodles {m}',cuisine='Chinese',price_paise=10000+m) for m in range(100)])
        db.commit()
    loaded=[]
    def record(session,obj):
        if isinstance(obj,MenuItem):loaded.append(obj.id)
    event.listen(OrmSession,'loaded_as_persistent',record)
    try:
        response=client.post('/search',json={'query':'Chinese Hakka noodles under 500','area':'Bandra','include_samples':False})
        assert response.status_code==200,response.text
        assert len(response.json()['results'])==30
        assert len(loaded)<=30
        assert all(row['dish']['price_paise']==10000 for row in response.json()['results'])
    finally:event.remove(OrmSession,'loaded_as_persistent',record)

def test_explicit_other_brand_or_branch_is_not_published():
    raw=snapshot();raw['menu']['source_url']='https://www.zomato.com/mumbai/unrelated-brand-bandra-west/order'
    with pytest.raises(ValueError,match='different brand'):prepare_snapshot(raw)
    raw=snapshot();raw['listing']['locality']='Bandra West';raw['menu']['source_url']='https://www.zomato.com/mumbai/fixture-kitchen-borivali/order'
    with pytest.raises(ValueError,match='different area'):prepare_snapshot(raw)

def test_worker_refreshes_reviewed_api_source_and_rate_limit_defers_all_api_jobs(client,monkeypatch):
    import asyncio,httpx
    import app.public_menu_api as api
    from app.catalog_worker import run_one
    from app.database import CatalogJob
    pg()
    with Session() as db:
        r=venue(db);persist_snapshots(db,[prepare_snapshot(snapshot())]);db.commit()
        source=db.scalar(select(CatalogSource).where(CatalogSource.restaurant_id==r.id))
        sid=source.id
        db.add(CatalogJob(source_id=sid));db.commit()
    async def successful(source,identity):return prepare_snapshot(snapshot())
    monkeypatch.setattr(api,'fetch_snapshot',successful)
    result=asyncio.run(run_one())
    assert result['state']=='succeeded' and result['source_kind']=='indiarestros_api'
    with Session() as db:
        other=Restaurant(name='Fixture other',address='Synthetic only',area='Bandra',latitude=19.06,longitude=72.83,cuisine='Chinese',sample=False,source_id='osm:node:other-fixture')
        db.add(other);db.flush()
        feed=CatalogSource(kind='indiarestros_api',url='https://indiarestros.com/api/v1/restaurants/IRR-0000000002/menu',restaurant_id=other.id,area='Bandra',permission_note='Synthetic fixture')
        db.add(feed);db.flush()
        db.add_all([CatalogJob(source_id=sid),CatalogJob(source_id=feed.id)]);db.commit();other_sid=feed.id
    async def limited(source,identity):
        request=httpx.Request('GET',source.url)
        response=httpx.Response(429,headers={'Retry-After':'120'},request=request)
        raise httpx.HTTPStatusError('Rate limited',request=request,response=response)
    monkeypatch.setattr(api,'fetch_snapshot',limited)
    result=asyncio.run(run_one());assert result['state']=='queued'
    with Session() as db:
        current=db.get(CatalogJob,result['job_id'])
        other_job=db.scalar(select(CatalogJob).where(CatalogJob.source_id==other_sid,CatalogJob.state=='queued'))
        assert other_job.available_at>=current.available_at
    assert asyncio.run(run_one()) is None


def test_undated_or_old_secondary_prices_require_review():
    raw=snapshot();raw['menu']['updated']=None
    with pytest.raises(ValueError,match='observation date required'):prepare_snapshot(raw)
    raw=snapshot();raw['menu']['updated']=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat()
    with pytest.raises(ValueError,match='older than 90 days'):prepare_snapshot(raw)
    raw=snapshot();raw['menu']['currency']='USD'
    with pytest.raises(ValueError,match='currency'):prepare_snapshot(raw)
