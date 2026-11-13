import json
from pathlib import Path
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy import select,func
from test_api import client,account,restaurant
from app.agents import parse_local,Intent
from app.saarthi import continued_intent,opening_status
from app.database import Session,MenuItem,User,AgentRun,Campaign,CampaignPolicy,Search,Transaction

@pytest.mark.parametrize('case',json.loads((Path(__file__).parent/'fixtures/mumbai_queries.json').read_text()),ids=lambda c:c['query'])
def test_golden_mumbai_queries(case):
    data=parse_local(case['query']).model_dump()
    assert {k:data[k] for k in case['expected']}==case['expected']

def test_devanagari_and_conversation_context():
    intent=parse_local('चाइनीज हक्का नूडल्स 300 रुपये 2 किमी बांद्रा')
    assert (intent.dish,intent.max_budget,intent.radius_km,intent.location)==('hakka noodles',300,2,'Bandra')
    next_intent=continued_intent('isme se sabse paas?',parse_local('isme se sabse paas?'),intent.model_dump())
    assert (next_intent.dish,next_intent.max_budget,next_intent.radius_km,next_intent.sort)==('hakka noodles',300,2,'distance')
    assert continued_intent('pizza under 500',parse_local('pizza under 500'),intent.model_dump()).dish=='pizza'

def test_verdict_stream_preserves_real_constraints_and_logs_actual_run(client):
    response=client.post('/query/stream',json={'query':'Chinese Hakka noodles 300 mein 2 km ke andar Bandra mein','research':False})
    assert response.status_code==200
    frames=[frame for frame in response.text.split('\n\n') if frame.startswith('event:')]
    events=[frame.split('\n')[0][7:] for frame in frames]
    assert events==['status','intent','candidates_found','menu_checked','price_filtered','verified','offers_applied','verdict']
    data=json.loads(frames[-1].split('data: ',1)[1]);assert data['verdict']['match_count']==1
    assert data['intent']['dish']=='hakka noodles'
    assert data['results'][0]['dish']['price_paise']==24000
    assert not data['results'][0]['confidence']['independently_verified']
    assert data['results'][0]['platform_links']['presence'].startswith('Not checked')
    wall=client.get('/agents/activity').json();assert wall['agents'][0]['agent']=='Saarthi'
    assert 'query' not in json.dumps(wall['agents'])
    assert wall['agents'][0]['cost_microrupees']==0

def test_diet_and_open_unknowns_fail_closed_and_group_budget_is_not_a_meal_claim(client):
    unknown=client.post('/search',json={'query':'vegetarian hakka noodles under 300'}).json();assert unknown['results']==[]
    with Session() as db:
        item=db.scalar(select(MenuItem).where(MenuItem.name=='Hakka noodles'));item.dietary='vegetarian';db.commit()
    known=client.post('/search',json={'query':'vegetarian hakka noodles under 300'}).json();assert known['results']
    assert client.post('/search',json={'query':'Hakka noodles under 300 open now'}).json()['results']==[]
    group=client.post('/search',json={'query':'4 log ke liye pizza ₹1500 tak delivery'}).json()
    assert 'individual menu-item prices' in group['verdict']['party_notice']
    assert opening_status('Unknown')['open'] is None
    assert opening_status('24/7')['open'] is True

def test_unique_query_credit_and_tiers_cannot_be_farmed_by_repeats(client):
    auth=account(client)
    for _ in range(6):assert client.post('/search',headers=auth,json={'query':'Chinese Hakka noodles under 300'}).status_code==200
    me=client.get('/me',headers=auth).json();assert me['searches']==6
    assert me['rewards']['meaningful_queries_30d']==1;assert me['rewards']['tier']=='Bronze'
    for q in ['biryani','dosa','sushi','pizza']:client.post('/search',headers=auth,json={'query':q})
    assert client.get('/me',headers=auth).json()['rewards']['tier']=='Silver'
    assert client.get('/admin/quality',headers=auth).status_code==403
    assert client.post('/auth/register',json={'name':'Bad','email':'admin@example.test','password':'example-passphrase','role':'admin'}).status_code==422


def test_missing_menu_research_persists_evidence_and_updates_the_lake(client,monkeypatch):
    import httpx
    from app.database import Restaurant,CatalogSource,ResearchRequest,BronzeArtifact,CatalogJob
    # Only the external HTTP response is synthetic; parsing, scheduling, database publication and re-query are real.
    html='<script type="application/ld+json">'+json.dumps({'@type':'MenuItem','name':'Hakka noodles','offers':{'price':'199','priceCurrency':'INR'}})+'</script>'
    original=httpx.AsyncClient
    def fetch(request):
        return httpx.Response(404) if request.url.path=='/robots.txt' else httpx.Response(200,text=html)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(fetch),**kw))
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menus.example.test')
    with Session() as db:
        restaurant=Restaurant(name='Synthetic research fixture',address='Synthetic Bandra fixture',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese',sample=False)
        db.add(restaurant);db.flush();rid=restaurant.id
        db.add(CatalogSource(kind='approved_menu',url='https://menus.example.test/food',restaurant_id=rid,area='Bandra',permission_note='Synthetic approved publisher fixture',enabled=True));db.commit()
    first=client.post('/query/stream',json={'query':'Hakka noodles under 300 in Bandra','include_samples':False})
    frame=next(f for f in first.text.split('\n\n') if f.startswith('event: verdict'));data=json.loads(frame.split('data: ',1)[1])
    assert data['results']==[] and data['research']['state']=='queued'
    status=client.get('/research/'+data['research']['token']).json();assert status['state']=='completed' and status['succeeded']==1
    second=client.post('/search',json={'query':'Hakka noodles under 300 in Bandra','include_samples':False,'research':False}).json()
    assert second['results'][0]['restaurant']['id']==rid and second['results'][0]['dish']['price_paise']==19900
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(BronzeArtifact))==1
        assert db.scalar(select(func.count()).select_from(ResearchRequest))==1
    assert client.get('/admin/quality').status_code==401


def test_claim_is_pending_until_admin_checks_business_and_contact(client):
    from app.database import Restaurant
    with Session() as db:
        row=Restaurant(name='Synthetic claim fixture',address='Synthetic Bandra fixture',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese',sample=False);db.add(row);db.commit();rid=row.id
    claimant=account(client,'claimant@example.test','owner');other=account(client,'other-owner@example.test','owner')
    claim=client.post('/partner/claim',headers=claimant,json={'restaurant_id':rid,'business_reference':'12345678901234'});assert claim.status_code==200,claim.text
    cid=claim.json()['id'];assert claim.json()['state']=='pending'
    assert client.get('/portal/restaurants',headers=claimant).json()==[]
    assert client.post('/admin/claims/'+cid,headers=claimant,json={'decision':'approve','note':'Self approval forbidden','business_checked':True,'contact_checked':True}).status_code==403
    operator=account(client,'operator@example.test')
    with Session() as db:db.scalar(select(User).where(User.email=='operator@example.test')).role='admin';db.commit()
    assert client.post('/admin/claims/'+cid,headers=operator,json={'decision':'approve','note':'Missing independent checks'}).status_code==422
    approved=client.post('/admin/claims/'+cid,headers=operator,json={'decision':'approve','note':'Synthetic operator fixture checked business and contact','business_checked':True,'contact_checked':True});assert approved.status_code==200
    listings=client.get('/portal/restaurants',headers=claimant).json();assert listings[0]['id']==rid and not listings[0]['ownership_verified']
    assert client.get('/portal/restaurants/'+str(rid)+'/offer-suggestions',headers=other).status_code==403
    suggestion=client.get('/portal/restaurants/'+str(rid)+'/offer-suggestions',headers=claimant).json();assert suggestion['impressions_30d']==0 and 'not been published' in suggestion['suggestions'][0]['reason']


def test_above_budget_alternative_is_not_returned_as_a_budget_match(client):
    data=client.post('/search',json={'query':'Hakka noodles under 200 in Bandra'}).json()
    assert data['results']==[]
    assert data['alternatives'][0]['price_paise']==24000
    assert 'budget se upar' in data['verdict']['headline']
    assert data['alternatives'][0]['price_paise']>data['intent']['max_budget']*100


def test_ai_proposals_need_operator_review_and_expired_prices_cannot_be_approved(client):
    from app.database import Restaurant,CatalogSource,MenuEvidence
    from app.catalog import persist_menu
    operator=account(client,'quality-operator@example.test')
    with Session() as db:
        user=db.scalar(select(User).where(User.email=='quality-operator@example.test'));user.role='admin'
        row=Restaurant(name='Synthetic AI review fixture',address='Synthetic Bandra fixture',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese',sample=False);db.add(row);db.flush()
        source=CatalogSource(kind='approved_menu',url='https://menus.example.test/food',restaurant_id=row.id,area='Bandra',permission_note='Synthetic publisher fixture',enabled=True);db.add(source);db.flush()
        persist_menu(db,source,'Hakka noodles INR 199',[{'name':'Hakka noodles','price_paise':19900,'excerpt':'Hakka noodles INR 199','method':'Gemini + exact evidence validation'}]);db.commit()
        mid=db.scalar(select(MenuItem.id).where(MenuItem.restaurant_id==row.id));assert not db.get(MenuEvidence,mid).active
    assert client.post('/search',json={'query':'Hakka noodles under 300','include_samples':False}).json()['results']==[]
    assert client.post('/admin/quality/'+str(mid),headers=operator,json={'decision':'approve','note':'Synthetic source evidence reviewed'}).status_code==200
    assert client.post('/search',json={'query':'Hakka noodles under 300','include_samples':False}).json()['results']
    with Session() as db:db.get(MenuEvidence,mid).expires_at=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat();db.commit()
    assert client.post('/admin/quality/'+str(mid),headers=operator,json={'decision':'approve','note':'Expired observations cannot be revived'}).status_code==409


def test_unrecognised_zero_result_queries_do_not_earn_reward_credit(client):
    auth=account(client)
    for q in ['find asdfgh qwerty','find nonsenseabc xyz','']:
        assert client.post('/search',headers=auth,json={'query':q}).status_code==200
    assert client.get('/me',headers=auth).json()['rewards']['meaningful_queries_30d']==0
