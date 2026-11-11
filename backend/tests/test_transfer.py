import os
import pytest
from sqlalchemy import create_engine,select,text
from app.database import Base,User
from app.transfer_postgres import transfer

@pytest.fixture
def databases():
    source=os.getenv('TRANSFER_TEST_SOURCE_URL');target=os.getenv('TRANSFER_TEST_TARGET_URL')
    if not source or not target:pytest.skip('Set isolated TRANSFER_TEST_SOURCE_URL and TRANSFER_TEST_TARGET_URL fixtures')
    engines=[create_engine(url) for url in (source,target)]
    for engine in engines:
        if not engine.url.database.endswith('_test'):raise ValueError('Transfer tests require disposable databases ending in _test')
        Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with engines[0].begin() as db:
        db.execute(User.__table__.insert(),{'id':42,'email':'transfer@example.test','name':'Fixture','password_hash':'test-fixture-only','role':'customer','consent':False})
    yield engines
    for engine in engines:engine.dispose()


def test_transfer_audit_copy_hashes_ids_sequences_and_nonempty_refusal(databases):
    source,target=databases
    report=transfer(source,target)
    assert report['users']['rows']==1
    with target.connect() as db:assert db.scalar(select(User.id)) is None
    report=transfer(source,target,execute=True)
    assert report['users']=={'rows':1,'verified':True}
    with target.begin() as db:
        assert db.scalar(select(User.id))==42
        new=db.execute(User.__table__.insert().values(email='next@example.test',name='Next',password_hash='test-fixture',role='customer',consent=False).returning(User.id)).scalar_one()
        assert new==43
    with pytest.raises(ValueError,match='not empty'):transfer(source,target,execute=True)
    with source.connect() as db:assert db.scalar(select(User.id))==42


def test_unknown_source_column_refuses_without_changing_destination(databases):
    source,target=databases
    with source.begin() as db:db.execute(text('ALTER TABLE users ADD COLUMN unknown_future_field text'))
    with pytest.raises(ValueError,match='unknown columns'):transfer(source,target,execute=True)
    with target.connect() as db:assert db.scalar(select(User.id)) is None
