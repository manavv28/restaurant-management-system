import os,subprocess,sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import DBAPIError
from test_api import client
from app.database import Base,engine
from app.main import app

def test_production_refuses_ephemeral_sqlite():
    result=subprocess.run([sys.executable,'-m','app.cloud_run','serve'],env={**os.environ,'APP_ENV':'production','DATABASE_URL':'sqlite:///:memory:','PYTHONPATH':'backend'},capture_output=True,text=True)
    assert result.returncode!=0
    assert 'Production requires an explicit PostgreSQL' in result.stderr

def test_pre_migration_startup_fails_without_creating_tables(monkeypatch):
    Base.metadata.drop_all(engine)
    monkeypatch.setenv('AUTO_CREATE_SCHEMA','false')
    with pytest.raises(DBAPIError):
        with TestClient(app):pass
    assert 'restaurants' not in inspect(engine).get_table_names()

def test_collection_job_is_bounded(client,monkeypatch):
    import asyncio
    from app.cloud_run import collect
    import app.catalog_worker as worker
    calls=[]
    async def execute():
        calls.append(True);return {'job_id':1,'state':'succeeded'}
    monkeypatch.setattr(worker,'run_one',execute)
    asyncio.run(collect(2))
    assert len(calls)==2
