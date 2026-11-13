"""Regression coverage for the live audit's silent constraint failures."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func
from test_api import client, account, restaurant
from app.agents import parse_local, validated_proposal
from app.database import Session, MenuItem, Search, SearchMatch
from app.saarthi import confidence, continued_intent


@pytest.mark.parametrize('query,expected', [
    ('Mujhe Bandra mein 2 km ke andar 300 rupaye mein hakka noodles chahiye', 300),
    ('Hakka noodles three hundred rupees within 2 km', 300),
    ('Hakka noodles under three hundred within 2 km', 300),
    ('Hakka noodles teen sau rupaye mein', 300),
    ('हक्का नूडल्स ३०० रुपये २ किमी बांद्रा', 300),
    ('Hakka noodles under ₹1,00,000 for 2 people within 2 km', 100000),
    ('Hakka noodles for 2 people under 300 within 2 km', 300),
    ('Hakka noodles for 2 people within 2 km', 500),
])
def test_explicit_currency_and_voice_amounts(query, expected):
    assert parse_local(query).max_budget == expected


def test_hindi_budget_filters_database_prices_instead_of_retaining_default(client):
    owner=account(client,'budget-regression@example.test','owner');rid=restaurant(client,owner)
    client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':'Hakka noodles','cuisine':'Chinese','price_paise':35000})
    response=client.post('/search',json={'query':'Mujhe Bandra mein 2 km ke andar 300 rupaye mein hakka noodles chahiye','budget':500})
    assert response.status_code==200
    data=response.json()
    assert data['intent']['max_budget']==300
    assert data['results'] and all(row['dish']['price_paise']<=30000 for row in data['results'])
    assert rid not in [row['restaurant']['id'] for row in data['results']]


@pytest.mark.parametrize('place',['Thane','Navi Mumbai','Oshiwara'])
@pytest.mark.parametrize('stream',[False,True])
def test_unresolved_location_requires_clarification_without_substituting_area(client,place,stream):
    response=client.post('/search',json={'query':f'Hakka noodles under 300 within 2 km in {place}','area':'Bandra','stream':stream})
    assert response.status_code==200
    data=json.loads(next(frame.split('data: ',1)[1] for frame in response.text.split('\n\n') if frame.startswith('event: verdict'))) if stream else response.json()
    assert data['results']==[] and data['nearby_unpriced']==[]
    assert data['clarification']['requested']==place
    assert data['search_origin']['kind']=='unresolved'
    assert data['verdict']['requires_clarification']
    assert data['research']['state']=='idle'
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(SearchMatch))==0
        assert db.scalar(select(Search)).results==0


def test_models_cannot_widen_or_drop_explicit_constraints():
    query='vegan gluten-free hakka noodles under 300 within 2 km in Thane'
    local=parse_local(query)
    intent=validated_proposal(query,local,{'max_budget':1000,'radius_km':10,'location':'Bandra','unresolved_location':None,'diet':None,'dietary_constraints':[]})
    assert intent.max_budget==300 and intent.radius_km==2
    assert intent.location is None and intent.unresolved_location=='Thane'
    assert set(intent.dietary_constraints)=={'vegan','gluten-free'}
    follow=continued_intent('nearest',parse_local('nearest'),intent.model_dump())
    assert follow.unresolved_location=='Thane' and follow.dietary_constraints==intent.dietary_constraints


def test_unresolved_search_does_not_earn_query_reward_credit(client):
    auth=account(client,'clarification-rewards@example.test')
    client.post('/search',headers=auth,json={'query':'Hakka noodles in Thane'})
    assert client.get('/me',headers=auth).json()['rewards']['meaningful_queries_30d']==0


def test_multiple_dietary_requirements_are_anded_against_declared_labels(client):
    owner=account(client,'diet-regression@example.test','owner');rid=restaurant(client,owner)
    for price,diet in [(9000,'vegetarian'),(12000,'vegan'),(18000,'vegan,gluten-free')]:
        response=client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':'Hakka noodles '+str(price),'cuisine':'Chinese','price_paise':price,'dietary':diet})
        assert response.status_code==200,response.text
    data=client.post('/search',json={'query':'Gluten free vegan hakka noodles under 300 within 2 km in Bandra','include_samples':False}).json()
    assert set(data['intent']['dietary_constraints'])=={'vegan','gluten-free'}
    assert len(data['results'])==1 and data['results'][0]['dish']['price_paise']==18000
    assert 'explicitly declared' in data['verdict']['dietary_notice']
    with Session() as db:
        db.scalar(select(MenuItem).where(MenuItem.restaurant_id==rid,MenuItem.price_paise==18000)).available=False;db.commit()
    empty=client.post('/search',json={'query':'Gluten free vegan hakka noodles under 300','include_samples':False}).json()
    assert empty['results']==[] and empty['alternatives']==[]
    assert 'dietary labels' in empty['verdict']['headline']
    assert client.post(f'/portal/restaurants/{rid}/menu',headers=owner,json={'name':'Unknown dietary claim','cuisine':'Chinese','price_paise':10000,'dietary':'healthy'}).status_code==422


def test_budget_scope_selection_and_explicit_query_apply_to_both_search_paths(client):
    for stream in [False,True]:
        response=client.post('/search',json={'query':'Hakka noodles under 300 for 2 people','budget_scope':'total','stream':stream,'research':False})
        data=json.loads(next(frame.split('data: ',1)[1] for frame in response.text.split('\n\n') if frame.startswith('event: verdict'))) if stream else response.json()
        assert data['intent']['budget_scope']=='total'
        assert data['results']==[]
        assert data['alternatives'][0]['listed_subtotal_paise']==48000
    explicit=continued_intent('Hakka noodles under 300 per item',parse_local('Hakka noodles under 300 per item'),None,'total')
    assert explicit.budget_scope=='item'


def test_price_freshness_keeps_original_observation_separate_from_retrieval():
    old=(datetime.now(timezone.utc)-timedelta(days=27)).isoformat()
    recent=datetime.now(timezone.utc).isoformat()
    value=confidence({'source_observed_at':old,'source_retrieved_at':recent,'source_expires_at':recent},{'sample':False})
    assert value['age_days']==27 and value['may_have_changed']
    assert value['observed_at']==old and value['retrieved_at']==recent
    assert 'does not reconfirm' in value['freshness_notice']


def test_collection_review_stops_retries_and_scheduler_honors_the_review_deadline(client,monkeypatch):
    from app import catalog_worker as worker
    from app.database import CatalogJob,CatalogSource
    from test_catalog import source
    with Session() as db:
        entry=source(db);sid=entry.id;db.add(CatalogJob(source_id=sid));db.commit()
    async def invalid_source(entry):raise ValueError('Menu currency is not INR')
    monkeypatch.setattr(worker,'fetch_menu',invalid_source)
    first=asyncio.run(worker.run_one())
    assert first['state']=='failed' and first['review_required']
    with Session() as db:
        job=db.get(CatalogJob,first['job_id']);assert job.attempts==1
        job.finished_at=(datetime.now(timezone.utc)-timedelta(hours=7)).isoformat();db.commit()
        assert worker.schedule(db)==0
        assert worker.retry_cooldown(db.get(CatalogSource,sid),job)>=24


def test_scheduled_batch_does_not_discover_or_approve_new_sources(client,monkeypatch):
    from app import catalog_worker as worker
    from app.database import CatalogJob,CatalogSource
    from test_catalog import source,html
    with Session() as db:
        entry=source(db);db.add(CatalogJob(source_id=entry.id));db.commit()
    async def published_menu(entry):return html()
    monkeypatch.setattr(worker,'fetch_menu',published_menu)
    result=asyncio.run(worker.run_batch(3,10))
    assert result['succeeded']==1 and result['processed']==1
    with Session() as db:assert db.scalar(select(func.count()).select_from(CatalogSource))==1
    with pytest.raises(ValueError):asyncio.run(worker.run_batch(10000,10000))
