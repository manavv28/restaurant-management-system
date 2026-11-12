"""Validate all saved menus and choose one reviewed provider record per venue."""
import argparse,json,collections,hashlib
from pathlib import Path
from app.public_menu_api import prepare_snapshot,operator_sql
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--snapshots',required=True);p.add_argument('--output',required=True)
p.add_argument('--batch-size',type=int,default=10)
a=p.parse_args()
if not 1<=a.batch_size<=20:raise ValueError('Use 1–20 menus per transaction')
out=Path(a.output)
if (out/'plan.json').exists():raise ValueError('Use a new output directory; reviewed plans are immutable')
out.mkdir(parents=True,exist_ok=True);(out/'sql').mkdir(exist_ok=True)
by_venue=collections.defaultdict(list);rejected=collections.Counter();received=0
for file in sorted(Path(a.snapshots).glob('*.json')):
    received+=1
    try:
        prepared=prepare_snapshot(json.loads(file.read_text()))
        by_venue[prepared['target_source_id']].append(prepared)
    except (ValueError,KeyError,TypeError) as error:rejected[str(error)[:120]]+=1
selected=[];conflicts=[]
for target,rows in by_venue.items():
    # Use the most recently dated provider menu, then the closest reviewed point.
    # Price observations from different delivery platforms are never averaged.
    rows.sort(key=lambda r:(r['metadata'].get('provider_updated_at') or '',-r['metadata']['identity_match'].get('distance_m',0),r['provider_id']),reverse=True)
    selected.append(rows[0])
    if len(rows)>1:conflicts.append({'target_source_id':target,'selected':rows[0]['provider_id'],'alternatives':[r['provider_id'] for r in rows[1:]]})
selected.sort(key=lambda r:r['target_source_id'])
(out/'plan.json').write_text(json.dumps(selected,ensure_ascii=False,separators=(',',':')))
batches=[];current=[]
for menu in selected:
    candidate=current+[menu]
    if current and (len(candidate)>a.batch_size or len(json.dumps(candidate,ensure_ascii=False,separators=(',',':')).encode())>750000):
        batches.append(current);current=[]
    current.append(menu)
if current:batches.append(current)
for index,batch in enumerate(batches):
    sql=operator_sql(batch)
    if len(sql.encode())>1_500_000:raise ValueError('One menu exceeds the reviewable operator batch size')
    (out/'sql'/f'{index:04d}.sql').write_text(sql)

report={'provider':'IndiaRestros','terms':'https://indiarestros.com/terms','api_docs':'https://indiarestros.com/api/docs',
        'saved_menus_checked':received,'selected_venues':len(selected),'selected_price_facts':sum(len(s['items']) for s in selected),'publication_batches':len(batches),
        'rejected_menus':dict(rejected),'rejected_item_facts':sum(s['rejected_items'] for s in selected),
        'original_sources':dict(collections.Counter(s['metadata']['original_source'] for s in selected)),
        'provider_date_known':sum(bool(s['metadata']['provider_updated_at']) for s in selected),'alternative_provider_records':conflicts,
        'plan_sha256':hashlib.sha256((out/'plan.json').read_bytes()).hexdigest(),
        'price_scope':'Third-party listed INR prices, not restaurant-confirmed current quotes. Original dates and ordering context retained. No photographs or publisher descriptions imported.'}
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='alternative_provider_records'},ensure_ascii=False,indent=2))
