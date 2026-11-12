import copy,hashlib,json
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy import text,select,func
from test_api import client
from app.database import Session,Restaurant,User,IngestionLog,engine
from app.contact_enrichment import business_phone,prepare_contact,CONTACT_SQL,public_contact

def fixture():
    target={'source_id':'synthetic:contact','external_id':'IRR-0000000001','expected_name':'Synthetic Diner','area':'Bandra','latitude':19.06,'longitude':72.83}
    doc={'id':target['external_id'],'name':target['expected_name'],'lat':19.06,'lon':72.83,'updated':(datetime.now(timezone.utc)-timedelta(days=5)).isoformat(),'phones':[{'v':'+91 98765 43210','src':'website'}],'sources':[]}
    return target,doc

def prepared(target,doc):return prepare_contact(doc,target,datetime.now(timezone.utc).isoformat(),hashlib.sha256(b'synthetic').hexdigest())

def test_phone_identity_branch_dates_and_conflicts():
    assert business_phone('+91 (98765) 43210')=='+919876543210'
    assert business_phone('9876543210 or 9123456789') is None
    assert business_phone('0000000000') is None
    target,doc=fixture();assert prepared(target,doc)['phone']=='+919876543210'
    original=copy.deepcopy(doc);doc['phones'].append({'v':'9123456789','src':'google'})
    with pytest.raises(ValueError,match='Conflicting'):prepared(target,doc)
    doc=copy.deepcopy(original);doc['sources']=[{'url':'https://www.zomato.com/mumbai/other-brand-bandra-west'}]
    with pytest.raises(ValueError,match='different brand'):prepared(target,doc)
    doc=copy.deepcopy(original);doc['sources']=[{'url':'https://www.zomato.com/mumbai/synthetic-diner-andheri-west'}]
    with pytest.raises(ValueError,match='different area'):prepared(target,doc)
    doc=copy.deepcopy(original);doc['lat']=19.15
    with pytest.raises(ValueError,match='moved'):prepared(target,doc)
    doc=copy.deepcopy(original);doc['updated']=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat()
    with pytest.raises(ValueError,match='old source'):prepared(target,doc)

@pytest.mark.skipif(engine.dialect.name!='postgresql',reason='Atomic operator publication uses PostgreSQL')
def test_contact_publication_preserves_owner_existing_and_sample_contacts(client):
    target,doc=fixture();contact=prepared(target,doc)
    with Session() as db:
        owner=User(email='contact-owner@example.test',name='Synthetic owner',password_hash='fixture',role='owner');db.add(owner);db.flush()
        rows=[]
        for index in range(4):
            r=Restaurant(name='Synthetic Diner',address='Synthetic test address',area='Bandra',latitude=19.06,longitude=72.83,cuisine='Indian',source_id=target['source_id']+str(index),phone='Existing contact' if index==1 else '',owner_id=owner.id if index==2 else None,sample=index==3)
            db.add(r);rows.append(r)
        db.commit();ids=[r.id for r in rows]
        contacts=[{**contact,'target_source_id':r.source_id} for r in rows]
        result=db.execute(text(CONTACT_SQL),{'contact_data':json.dumps(contacts)}).mappings().one();db.commit()
        assert result['contacts_added']==result['evidence_rows']==1
        result=db.execute(text(CONTACT_SQL),{'contact_data':json.dumps(contacts)}).mappings().one();db.commit();assert result['contacts_added']==0
        db.expire_all();assert [db.get(Restaurant,i).phone for i in ids]==['+919876543210','Existing contact','','']
        assert db.scalar(select(func.count()).select_from(IngestionLog))==1
    result=client.get('/restaurants/'+str(ids[0]));assert result.status_code==200
    assert result.json()['restaurant']['phone_source']['source_url']==contact['source_url']
    with Session() as db:
        r=db.get(Restaurant,ids[0]);r.phone='Owner changed number';db.commit()
    assert 'phone_source' not in client.get('/restaurants/'+str(ids[0])).json()['restaurant']
