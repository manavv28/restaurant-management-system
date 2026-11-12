"""Synthetic fixtures for citywide import quality and identity preservation."""
import copy
import json
import pytest
from test_api import client
from app.city_catalog import normalize,IdentityMatcher

def fixture():
    return {'id':'00000000-0000-0000-0000-000000000001','names':{'primary':'Fixture Café'},
            'basic_category':'cafe','taxonomy':{'primary':'cafe'},'confidence':.8,'operating_status':None,
            'bbox':{'ymin':19.23,'ymax':19.23,'xmin':72.8567,'xmax':72.8567},
            'addresses':[{'locality':'Mumbai','postcode':'400092'}],
            'sources':[{'dataset':'Synthetic fixture','license':'CDLA-Permissive-2.0'}]}

def test_normalization_preserves_unknowns_and_provenance():
    row=normalize(fixture(),'test-release','test-time')
    assert row['area']=='Borivali' and row['cuisine']=='Unspecified'
    assert row['phone']=='' and row['website']==''
    assert 'rating' not in row and 'opening_hours' not in row and 'price_paise' not in row
    assert json.loads(row['details'])['confidence']==.8
    for key,value in [('confidence',.49),('operating_status','permanently_closed'),('basic_category','grocery')]:
        data=fixture();data[key]=value
        with pytest.raises(ValueError):normalize(data,'test','test')
    data=fixture();data['sources'][0]['license']='unknown'
    with pytest.raises(ValueError,match='unreviewed_licence'):normalize(data,'test','test')

def test_identity_matching_keeps_branches_and_existing_ids():
    row=normalize(fixture(),'test','test')
    existing={**row,'source_id':'osm:node:123','id':45,'owner_id':7}
    matcher=IdentityMatcher([existing])
    assert matcher.match_or_add(row)==('osm:node:123',True)
    branch=copy.deepcopy(row);branch['source_id']='overture:other';branch['latitude']+=.01
    assert matcher.match_or_add(branch)==('overture:other',False)
    assert matcher.match_or_add(branch)==('overture:other',True)
    assert existing['id']==45 and existing['owner_id']==7

def test_directory_bounds_filters_and_no_samples(client):
    from app.database import Session,Restaurant
    with Session() as db:
        for n in range(3):
            db.add(Restaurant(name=f'Fixture city venue {n}',address='Test only',area='Borivali',latitude=19.23,longitude=72.8567,cuisine='Unspecified',sample=False))
        db.commit()
    first=client.get('/catalog/restaurants',params={'q':'Fixture city','area':'Borivali','limit':2}).json()
    assert len(first['restaurants'])==2 and first['next_cursor']
    second=client.get('/catalog/restaurants',params={'q':'Fixture city','after':first['next_cursor']}).json()
    assert len(second['restaurants'])==1 and second['next_cursor'] is None
    assert client.get('/catalog/restaurants?limit=100000').status_code==422
    assert client.get('/catalog/restaurants?area=Delhi').status_code==422
    assert client.get('/catalog/restaurants?q=%25').json()['restaurants']==[]
    assert 'Borivali' in client.get('/areas').json()

def test_import_sql_repeats_without_changing_metadata_or_menus(client):
    import runpy
    from pathlib import Path
    from sqlalchemy import text
    from app.database import Session,Restaurant,MenuItem,engine
    if engine.dialect.name!='postgresql':pytest.skip('PostgreSQL fixture required for JSONB import')
    build=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/catalog/build_import_sql.py'))['batch_sql']
    row=normalize(fixture(),'test','2026-11-12T00:00:00+00:00')
    with Session() as db:
        r=Restaurant(name='Preserved owner name',address='Owner address',area='Borivali',latitude=row['latitude'],longitude=row['longitude'],cuisine='Indian',source_id='osm:node:fixture',sample=False)
        db.add(r);db.flush()
        menu=MenuItem(restaurant_id=r.id,name='Owner menu fixture',cuisine='Indian',price_paise=10000)
        db.add(menu);db.commit();rid=r.id;mid=menu.id
    row['target_source_id']='osm:node:fixture'
    new=copy.deepcopy(row);new['external_id']='00000000-0000-0000-0000-000000000002';new['source_id']='overture:'+new['external_id'];new['target_source_id']=new['source_id']
    for _ in range(2):
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as db:
            db.exec_driver_sql(build([row,new]))
    with Session() as db:
        assert db.get(Restaurant,rid).name=='Preserved owner name'
        assert db.get(MenuItem,mid).price_paise==10000
        assert db.scalar(text("select count(*) from restaurants where source_id=:sid"),{'sid':new['source_id']})==1
        assert db.scalar(text("select count(*) from catalog_identities"))==2
        assert db.scalar(text("select restaurant_id from catalog_identities where external_id=:id"),{'id':row['external_id']})==rid
