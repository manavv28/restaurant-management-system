"""One image for Cloud Run API, bounded collection jobs and schema migrations."""
import argparse
import asyncio
import hashlib
import os
from pathlib import Path
from sqlalchemy import select
from .database import Base, engine, Session, CatalogSource
from .catalog import OSM_URL
from .agents import AREAS

def migrate(directory=None):
    if engine.dialect.name!='postgresql':
        raise RuntimeError('Deployment migrations require PostgreSQL, never ephemeral SQLite')
    directory=Path(directory or os.getenv('MIGRATIONS_DIR','/app/migrations'))
    files=sorted(directory.glob('*.sql'))
    if not files:raise RuntimeError('No migration files found')
    raw=engine.raw_connection()
    try:
        with raw.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(9100801)')
            cursor.execute('CREATE TABLE IF NOT EXISTS biteai_migrations (name text PRIMARY KEY, sha256 text NOT NULL)')
            cursor.execute('ALTER TABLE biteai_migrations ENABLE ROW LEVEL SECURITY')
            cursor.execute('REVOKE ALL ON TABLE biteai_migrations FROM anon, authenticated')
            for file in files:
                sql=file.read_text();digest=hashlib.sha256(sql.encode()).hexdigest()
                cursor.execute('SELECT sha256 FROM biteai_migrations WHERE name=%s',(file.name,))
                previous=cursor.fetchone()
                if previous:
                    if previous[0]!=digest:raise RuntimeError('Previously applied migration changed: '+file.name)
                    continue
                cursor.execute(sql,prepare=False)
                cursor.execute('INSERT INTO biteai_migrations(name,sha256) VALUES (%s,%s)',(file.name,digest))
                print('Applied '+file.name,flush=True)
        raw.commit()
    except Exception:
        raw.rollback();raise
    finally:raw.close()

async def collect(limit):
    from .catalog_worker import schedule, run_one
    with Session() as db:
        for area in AREAS:
            if not db.scalar(select(CatalogSource.id).where(CatalogSource.kind=='osm',CatalogSource.area==area)):
                db.add(CatalogSource(kind='osm',url=OSM_URL,area=area,permission_note='OpenStreetMap ODbL; retain attribution and share-alike obligations',refresh_hours=168))
        db.commit();schedule(db)
    failed=False
    for _ in range(limit):
        result=await run_one()
        if result is None:break
        print(__import__('json').dumps(result),flush=True)
        if result['state']!='succeeded':failed=True
    if failed:raise RuntimeError('One or more collection jobs failed or need retry; inspect catalog job status')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['serve','migrate','collect','retain'],default='serve',nargs='?')
    parser.add_argument('--limit',type=int,default=5)
    args=parser.parse_args()
    if os.getenv('APP_ENV')=='production':
        url=os.getenv('DATABASE_URL','')
        if not url.startswith(('postgres://','postgresql://','postgresql+psycopg://')):
            raise RuntimeError('Production requires an explicit PostgreSQL DATABASE_URL')
    if args.mode=='serve':
        import uvicorn
        uvicorn.run('app.main:app',host='0.0.0.0',port=int(os.getenv('PORT','8080')),workers=1)
    elif args.mode=='migrate':migrate()
    elif args.mode=='collect':
        if not 1<=args.limit<=50:raise ValueError('Collection limit must be 1–50')
        asyncio.run(collect(args.limit))
    else:
        from .jobs import retain
        retain()
if __name__=='__main__':main()
