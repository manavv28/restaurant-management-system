"""Durable job runner: python -m app.catalog_worker --seed-osm --schedule --once."""
import argparse
import asyncio
import json
import logging
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, Session, CatalogSource, CatalogJob, now
from .catalog import future, discover_osm, import_osm, fetch_menu, structured_menu, ai_menu, persist_menu, OSM_URL
from .agents import AREAS

# UI search coverage must never silently expand public-provider collection.
DEFAULT_OSM_AREAS=('Bandra','Andheri','Powai','Colaba','Dadar')

def seed_osm_sources(db,areas=None):
    selected=DEFAULT_OSM_AREAS if areas is None else tuple(areas)
    if any(area not in AREAS for area in selected):raise ValueError('Unknown collection area')
    for area in selected:
        if not db.scalar(select(CatalogSource.id).where(CatalogSource.kind=='osm',CatalogSource.area==area)):
            db.add(CatalogSource(kind='osm',url=OSM_URL,area=area,permission_note='OpenStreetMap ODbL; retain attribution and comply with database share-alike obligations',refresh_hours=168))
    db.commit()

def retry_delay_hours(exc,attempts):
    """Bounded exponential backoff; respect numeric and HTTP-date Retry-After."""
    seconds=min(3600,60*2**max(0,attempts-1))
    if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in (429,503):
        value=exc.response.headers.get('Retry-After','3600')
        try:seconds=max(seconds,float(value))
        except ValueError:
            try:seconds=max(seconds,(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
            except (ValueError,TypeError,OverflowError):seconds=max(seconds,3600)
    return max(60,min(seconds,86400))/3600


def retry_cooldown(source,latest):
    # Repeated extraction/identity/robots failures need source review, not an hourly storm.
    review=latest.error and any(word in latest.error.lower() for word in ('robots','unambiguous','identity','different brand','different area','disabled','unsupported','http 403','http 404','http 410'))
    return max(24,source.refresh_hours) if review else 6


def schedule(db):
    queued=0
    for source in db.scalars(select(CatalogSource).where(CatalogSource.enabled.is_(True))).all():
        if source.checked_at and source.checked_at>=(datetime.now(timezone.utc)-timedelta(hours=source.refresh_hours)).isoformat():continue
        if db.scalar(select(CatalogJob.id).where(CatalogJob.source_id==source.id,CatalogJob.state.in_(['queued','running']))):continue
        latest=db.scalar(select(CatalogJob).where(CatalogJob.source_id==source.id).order_by(CatalogJob.id.desc()).limit(1))
        if latest and latest.state=='failed' and latest.finished_at and latest.finished_at>=(datetime.now(timezone.utc)-timedelta(hours=retry_cooldown(source,latest))).isoformat():continue
        db.add(CatalogJob(source_id=source.id))
        try:db.commit();queued+=1
        except IntegrityError:db.rollback()
    db.commit();return queued

async def run_one(job_id=None):
    with Session() as db:
        # Recover leases after a worker crash. Three attempts max.
        stale=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
        for row in db.scalars(select(CatalogJob).where(CatalogJob.state=='running',CatalogJob.started_at<stale)):
            row.state='queued' if row.attempts<3 else 'failed';row.error='Worker lease expired'
            if row.state=='failed':row.finished_at=now()
        db.commit()
        candidates=db.scalars(select(CatalogJob).where(CatalogJob.state=='queued',CatalogJob.available_at<=now()).where(CatalogJob.id==job_id if job_id else True).order_by(CatalogJob.id).limit(20)).all()
        job=None
        for candidate in candidates:
            claimed=db.execute(update(CatalogJob).where(CatalogJob.id==candidate.id,CatalogJob.state=='queued').values(state='running',started_at=now(),attempts=CatalogJob.attempts+1))
            db.commit()
            if claimed.rowcount:job=db.get(CatalogJob,candidate.id);break
        if not job:return None
        source=db.get(CatalogSource,job.source_id)
        trace=[];job_id=job.id
        db.commit()
        try:
            if not source or not source.enabled:raise ValueError('Source disabled')
            if source.kind=='osm':
                payload=await discover_osm(source)
                trace.append({'agent':'Discovery','tool':'overpass','records':len(payload['elements'])})
                source=db.scalar(select(CatalogSource).where(CatalogSource.id==source.id).with_for_update().execution_options(populate_existing=True))
                if not source.enabled:raise ValueError('Source disabled')
                result=import_osm(db,payload,source.area)
            elif source.kind=='indiarestros_api':
                from .public_menu_api import fetch_snapshot,persist_snapshots,provider_id
                from .database import CatalogIdentity,Restaurant
                identity=db.get(CatalogIdentity,('indiarestros',provider_id(source.url)))
                if not identity or identity.restaurant_id!=source.restaurant_id:raise ValueError('Reviewed provider identity required')
                restaurant=db.get(Restaurant,source.restaurant_id)
                if not restaurant or restaurant.owner_id is not None:
                    source.enabled=False;db.commit();raise ValueError('Owner-managed public API source disabled')
                db.commit()
                snapshot=await fetch_snapshot(source,identity)
                result=persist_snapshots(db,[snapshot])
                trace.append({'agent':'Public menu API','tool':'attributed_INR_price_facts','output':result})
            elif source.kind=='approved_menu':
                html=await fetch_menu(source);observed_url=source.url
                from .saarthi import save_bronze
                save_bronze(db,source.id,html);db.commit()
                trace.append({'agent':'Collection','tool':'approved_https_and_robots','bytes':len(html.encode())})
                items,text=structured_menu(html)
                method=items[0].get('method','schema.org') if items else 'no structured prices'
                if not items:
                    from .discovery import menu_candidates
                    from types import SimpleNamespace
                    for candidate in menu_candidates(html,source.url)[:3]:
                        candidate_html=await fetch_menu(SimpleNamespace(url=candidate))
                        candidate_items,candidate_text=structured_menu(candidate_html)
                        if candidate_items:
                            html=candidate_html;items=candidate_items;text=candidate_text;observed_url=candidate
                            save_bronze(db,source.id,html);db.commit()
                            method=items[0].get('method','schema.org')
                            trace.append({'agent':'Source discovery','tool':'approved_menu_link','url':candidate})
                            break
                if not items:
                    items,note=await ai_menu(text);method=note
                trace.append({'agent':'Menu intelligence','tool':method,'extracted':len(items)})
                if not items:raise ValueError('No unambiguous INR menu items extracted; review source or configure Gemini')
                source=db.scalar(select(CatalogSource).where(CatalogSource.id==source.id).with_for_update().execution_options(populate_existing=True))
                if not source.enabled:raise ValueError('Source disabled')
                result=persist_menu(db,source,html,items,page_url=observed_url)
            else:raise ValueError('Unsupported source kind')
            trace.append({'agent':'Data lake','tool':'source_deduplication_and_upsert','output':result})
            source.checked_at=now();job.state='succeeded';job.error=None;job.finished_at=now()
            job.trace=json.dumps(trace);db.commit()
            return {'job_id':job.id,'state':job.state,'trace':trace,'source_kind':source.kind}
        except Exception as exc:
            jid=job_id
            db.rollback()
            job=db.get(CatalogJob,jid)
            if isinstance(exc,httpx.HTTPStatusError):error=f'Provider returned HTTP {exc.response.status_code}'
            elif isinstance(exc,ValueError):error=str(exc)[:200]
            else:error=f'{type(exc).__name__}: source operation failed'
            job.error=error;job.state='queued' if job.attempts<3 and source and source.enabled else 'failed'
            delay=retry_delay_hours(exc,job.attempts)
            job.available_at=future(delay);job.trace=json.dumps(trace)
            if source and source.kind=='indiarestros_api' and isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code==429:
                db.execute(update(CatalogJob).where(CatalogJob.source_id.in_(select(CatalogSource.id).where(CatalogSource.kind=='indiarestros_api')),CatalogJob.state=='queued',CatalogJob.available_at<job.available_at).values(available_at=job.available_at))
            if job.state=='failed':job.finished_at=now()
            db.commit()
            return {'job_id':job.id,'state':job.state,'error':error}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed-osm',action='store_true')
    parser.add_argument('--osm-area',action='append',choices=tuple(AREAS),help='Explicit collection area; defaults to the original five, independently of search coverage')
    parser.add_argument('--schedule',action='store_true')
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--loop',action='store_true')
    args=parser.parse_args()
    import os
    if os.getenv('AUTO_CREATE_SCHEMA','false' if os.getenv('APP_ENV')=='production' else 'true').lower()=='true':
        Base.metadata.create_all(engine)
    with Session() as db:
        if args.seed_osm:seed_osm_sources(db,args.osm_area)
        if args.schedule:print(json.dumps({'queued':schedule(db)}))
    if args.loop:
        async def loop():
            while True:
                try:
                    with Session() as db:schedule(db)
                    # Serial bounded batches keep API load controlled.
                    for _ in range(5):
                        result=await run_one();print(json.dumps(result),flush=True)
                        if not result or result.get('source_kind')!='indiarestros_api' or result['state']!='succeeded':break
                except Exception:
                    logging.exception('Catalogue cycle failed; supervisor will retry in 30 seconds')
                await asyncio.sleep(30)
        asyncio.run(loop())
    if args.once:
        result=asyncio.run(run_one());print(json.dumps(result))
        if result and result['state']!='succeeded':raise SystemExit(1)
if __name__=='__main__':main()
