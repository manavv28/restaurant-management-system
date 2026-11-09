"""Copy application rows into an EMPTY PostgreSQL destination; never reset data."""
import argparse
import getpass
import hashlib
import json
import os
from sqlalchemy import create_engine, inspect, select, func, text
from .database import Base

def postgres_engine(url):
    if url.startswith('postgres://'):url=url.replace('postgres://','postgresql+psycopg://',1)
    elif url.startswith('postgresql://'):url=url.replace('postgresql://','postgresql+psycopg://',1)
    if not url.startswith('postgresql+psycopg://'):raise ValueError('Both databases must use PostgreSQL')
    return create_engine(url,pool_pre_ping=True,hide_parameters=True)

def fingerprint(rows):
    digest=hashlib.sha256();count=0
    for row in rows:
        digest.update(json.dumps(dict(row),sort_keys=True,default=str,separators=(',',':')).encode());count+=1
    return count,digest.hexdigest()

def transfer(source_engine,target_engine,execute=False):
    if source_engine.dialect.name!='postgresql' or target_engine.dialect.name!='postgresql':raise ValueError('PostgreSQL is required')
    report={}
    # A read-only repeatable snapshot prevents changes to the source by this tool.
    with source_engine.connect().execution_options(isolation_level='REPEATABLE READ') as source, target_engine.begin() as target:
        source.exec_driver_sql('SET TRANSACTION READ ONLY')
        target.execute(text('SELECT pg_advisory_xact_lock(9100801)'))
        source_tables=set(inspect(source).get_table_names())
        target_tables=set(inspect(target).get_table_names())
        tables=list(Base.metadata.sorted_tables)
        missing={t.name for t in tables}-target_tables
        if missing:raise ValueError('Apply destination schema migrations first; missing tables: '+', '.join(sorted(missing)))
        # Lock application tables against concurrent destination writes for this transaction.
        names=', '.join(target.dialect.identifier_preparer.quote(t.name) for t in tables)
        target.exec_driver_sql('LOCK TABLE '+names+' IN SHARE ROW EXCLUSIVE MODE')
        for table in tables:
            if target.scalar(select(func.count()).select_from(table)):
                raise ValueError('Destination is not empty; no rows were changed')
        for table in tables:
            if table.name not in source_tables:
                report[table.name]={'rows':0,'note':'Table absent from older source release'};continue
            old_columns={c['name'] for c in inspect(source).get_columns(table.name)}
            if old_columns-{c.name for c in table.columns}:raise ValueError('Source schema has unknown columns; upgrade the transfer tool before copying')
            columns=[c for c in table.columns if c.name in old_columns]
            query=select(*columns).order_by(*table.primary_key.columns)
            if not execute:
                report[table.name]={'rows':source.scalar(select(func.count()).select_from(table))};continue
            rows=source.execute(query.execution_options(yield_per=500)).mappings()
            expected=hashlib.sha256();count=0;batch=[]
            for row in rows:
                value=dict(row);batch.append(value);count+=1
                expected.update(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode())
                if len(batch)==500:target.execute(table.insert(),batch);batch=[]
            if batch:target.execute(table.insert(),batch)
            actual_count,actual_hash=fingerprint(target.execute(query).mappings())
            if actual_count!=count or actual_hash!=expected.hexdigest():raise RuntimeError('Copy verification failed for '+table.name)
            for column in table.primary_key.columns:
                if not isinstance(column.type,__import__('sqlalchemy').Integer):continue
                sequence=target.scalar(text('SELECT pg_get_serial_sequence(:table,:column)'),{'table':table.name,'column':column.name})
                if sequence:
                    maximum=target.scalar(select(func.max(column)))
                    target.execute(text('SELECT setval(:sequence,:value,:called)'),{'sequence':sequence,'value':max(1,maximum or 1),'called':maximum is not None})
            report[table.name]={'rows':count,'verified':True}
        if not execute:target.rollback()
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copy',action='store_true',help='Actually copy rows; default is a read-only audit')
    args=parser.parse_args()
    source_url=os.getenv('SOURCE_DATABASE_URL') or getpass.getpass('Render external database URL (hidden): ')
    target_url=os.getenv('TARGET_DATABASE_URL') or getpass.getpass('Supabase session-pooler URL (hidden): ')
    try:source=postgres_engine(source_url);target=postgres_engine(target_url)
    except Exception:raise SystemExit('Invalid PostgreSQL URL; check the hidden connection settings')
    try:
        print(json.dumps({'mode':'copied' if args.copy else 'audit','tables':transfer(source,target,args.copy)},indent=2))
    except Exception as exc:
        # Avoid including credential-bearing URLs or row contents in diagnostic output.
        if isinstance(exc,ValueError):raise SystemExit(str(exc))
        raise SystemExit(type(exc).__name__+': operation failed; transaction rolled back. Check database access/schema privately.')
    finally:source.dispose();target.dispose()

if __name__=='__main__':main()
