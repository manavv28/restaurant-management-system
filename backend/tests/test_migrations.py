"""Read-only checks against a freshly migrated isolated PostgreSQL database."""
import os
import pytest
from sqlalchemy import create_engine,inspect,text
from app.database import Base

@pytest.fixture
def migrated():
    url=os.getenv('MIGRATION_TEST_DATABASE_URL')
    if not url:pytest.skip('Set MIGRATION_TEST_DATABASE_URL to an isolated migrated PostgreSQL fixture')
    engine=create_engine(url)
    yield engine
    engine.dispose()


def test_sql_migrations_match_orm_columns(migrated):
    inspector=inspect(migrated)
    for table in Base.metadata.sorted_tables:
        actual={c['name']:c for c in inspector.get_columns(table.name)}
        assert set(actual)==set(table.c.keys()),table.name
        for column in table.c:
            assert actual[column.name]['nullable']==column.nullable,(table.name,column.name)
            assert actual[column.name]['type']._type_affinity==column.type._type_affinity,(table.name,column.name)


def test_browser_roles_cannot_access_application_tables(migrated):
    with migrated.connect() as db:
        for table in Base.metadata.sorted_tables:
            assert db.scalar(text("select relrowsecurity from pg_class where oid=to_regclass(:name)"),{'name':'public.'+table.name})
            for role in ('anon','authenticated'):
                assert not db.scalar(text("select has_table_privilege(:role,:name,'SELECT,INSERT,UPDATE,DELETE')"),{'role':role,'name':'public.'+table.name})


def test_migration_history_records_all_files(migrated):
    from pathlib import Path
    import hashlib
    files=Path(__file__).resolve().parents[2]/'supabase/migrations'
    with migrated.connect() as db:
        rows=dict(db.execute(text('select name,sha256 from biteai_migrations')).all())
    assert rows=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files.glob('*.sql')}


def test_migrated_dietary_constraint_accepts_declared_combinations_and_rejects_other_claims(migrated):
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    from app.database import Restaurant,MenuItem
    with Session(migrated) as db:
        row=Restaurant(name='Isolated dietary migration fixture',address='Test Bandra address',area='Bandra',latitude=19.0596,longitude=72.8295,cuisine='Chinese',sample=False)
        db.add(row);db.flush()
        item=MenuItem(restaurant_id=row.id,name='Hakka noodles fixture',cuisine='Chinese',price_paise=20000,dietary='vegan,gluten-free')
        db.add(item);db.flush()
        assert db.get(MenuItem,item.id).dietary=='vegan,gluten-free'
        with pytest.raises(IntegrityError):
            with db.begin_nested():
                item.dietary='healthy';db.flush()
        db.rollback()
