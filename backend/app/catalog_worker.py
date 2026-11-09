"""Durable job runner: python -m app.catalog_worker --seed-osm --schedule --once."""
import argparse
import asyncio
import json
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, Session, CatalogSource, CatalogJob, now
from .catalog import future, discover_osm, import_osm, fetch_menu, structured_menu, ai_menu, persist_menu, OSM_URL
from .agents import AREAS

def schedule(db):
    queued=0
    for source in db.scalars(select(CatalogSource).where(CatalogSource.enabled.is_(True))).all():
        if source.checked_at and source.checked_at>=(datetime.now(timezone.utc)-timedelta(hours=source.refresh_hours)).isoformat():continue
        if db.scalar(select(CatalogJob.id).where(CatalogJob.source_id==source.id,CatalogJob.state.in_(['queued','running']))):continue
        latest=db.scalar(select(CatalogJob).where(CatalogJob.source_id==source.id).order_by(CatalogJob.id.desc()).limit(1))
        if latest and latest.state=='failed' and latest.finished_at and latest.finished_at>=(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat():continue
        db.add(CatalogJob(source_id=source.id))
        try:db.commit();queued+=1
        except IntegrityError:db.rollback()
    db.commit();return queued

async def run_one():
    with Session() as db:
        # Recover leases after a worker crash. Three attempts max.
        stale=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
        for row in db.scalars(select(CatalogJob).where(CatalogJob.state=='running',CatalogJob.started_at<stale)):
            row.state='queued' if row.attempts<3 else 'failed';row.error='Worker lease expired'
        db.commit()
        candidates=db.scalars(select(CatalogJob).where(CatalogJob.state=='queued',CatalogJob.available_at<=now()).order_by(CatalogJob.id).limit(20)).all()
        job=None
        for candidate in candidates:
            claimed=db.execute(update(CatalogJob).where(CatalogJob.id==candidate.id,CatalogJob.state=='queued').values(state='running',started_at=now(),attempts=CatalogJob.attempts+1))
            db.commit()
            if claimed.rowcount:job=db.get(CatalogJob,candidate.id);break
        if not job:return None
        source=db.get(CatalogSource,job.source_id)
        trace=[]
        try:
            if not source or not source.enabled:raise ValueError('Source disabled')
            if source.kind=='osm':
                payload=await discover_osm(source)
                trace.append({'agent':'Discovery','tool':'overpass','records':len(payload['elements'])})
                result=import_osm(db,payload,source.area)
            elif source.kind=='approved_menu':
                html=await fetch_menu(source)
                trace.append({'agent':'Collection','tool':'approved_https_and_robots','bytes':len(html.encode())})
                items,text=structured_menu(html)
                method='schema.org'
                if not items:
                    items,note=await ai_menu(text);method=note
                trace.append({'agent':'Menu intelligence','tool':method,'extracted':len(items)})
                if not items:raise ValueError('No unambiguous INR menu items extracted; review source or configure Gemini')
                result=persist_menu(db,source,html,items)
            else:raise ValueError('Unsupported source kind')
            trace.append({'agent':'Data lake','tool':'source_deduplication_and_upsert','output':result})
            source.checked_at=now();job.state='succeeded';job.error=None;job.finished_at=now()
            job.trace=json.dumps(trace);db.commit()
            return {'job_id':job.id,'state':job.state,'trace':trace}
        except Exception as exc:
            jid=job.id
            db.rollback()
            job=db.get(CatalogJob,jid)
            if isinstance(exc,httpx.HTTPStatusError):error=f'Provider returned HTTP {exc.response.status_code}'
            elif isinstance(exc,ValueError):error=str(exc)[:200]
            else:error=f'{type(exc).__name__}: source operation failed'
            job.error=error;job.state='queued' if job.attempts<3 else 'failed'
            delay=2**job.attempts/60
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code==429:
                try:delay=max(delay,float(exc.response.headers.get('Retry-After','3600'))/3600)
                except ValueError:delay=max(delay,1)
            job.available_at=future(delay);job.trace=json.dumps(trace)
            if job.state=='failed':job.finished_at=now()
            db.commit()
            return {'job_id':job.id,'state':job.state,'error':error}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed-osm',action='store_true')
    parser.add_argument('--schedule',action='store_true')
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--loop',action='store_true')
    args=parser.parse_args()
    Base.metadata.create_all(engine)
    with Session() as db:
        if args.seed_osm:
            for area in AREAS:
                if not db.scalar(select(CatalogSource.id).where(CatalogSource.kind=='osm',CatalogSource.area==area)):
                    db.add(CatalogSource(kind='osm',url=OSM_URL,area=area,permission_note='OpenStreetMap ODbL; retain attribution and comply with database share-alike obligations',refresh_hours=168))
            db.commit()
        if args.schedule:print(json.dumps({'queued':schedule(db)}))
    if args.loop:
        async def loop():
            while True:
                with Session() as db:schedule(db)
                print(json.dumps(await run_one()),flush=True)
                await asyncio.sleep(30)
        asyncio.run(loop())
    if args.once:
        result=asyncio.run(run_one());print(json.dumps(result))
        if result and result['state']!='succeeded':raise SystemExit(1)
if __name__=='__main__':main()
