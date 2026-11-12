"""Prepare a reviewable citywide plan; optional shapely is an offline-only dependency.

Run with PYTHONPATH=backend and provide the public extract, district boundaries,
existing public restaurant metadata and output directory. No credentials required.
"""
import argparse,hashlib,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from shapely.geometry import Point,shape
from shapely.ops import unary_union
from app.city_catalog import normalize,IdentityMatcher,FOOD_CATEGORIES

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--extract',required=True);p.add_argument('--boundary',required=True)
p.add_argument('--existing',required=True);p.add_argument('--output',required=True)
p.add_argument('--release',required=True)
a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
region=unary_union([shape(f['geometry']) for f in json.loads(Path(a.boundary).read_text())['features']])
if not region.is_valid or region.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('Invalid district boundary')
matcher=IdentityMatcher(json.loads(Path(a.existing).read_text()));counts=Counter();records=[]
observed=datetime.now(timezone.utc).isoformat()
# Highest-confidence rows win when duplicate source rows have conflicting metadata.
rows=[]
for line in Path(a.extract).open():
    row=json.loads(line)
    if row.get('basic_category') not in FOOD_CATEGORIES:continue
    counts['food_candidates']+=1
    b=row['bbox'];lat=(b['ymin']+b['ymax'])/2;lon=(b['xmin']+b['xmax'])/2
    if not region.covers(Point(lon,lat)):counts['outside_district_boundary']+=1;continue
    rows.append(row)
for row in sorted(rows,key=lambda r:-(r.get('confidence') or 0)):
    try:record=normalize(row,a.release,observed)
    except ValueError as e:counts[str(e)]+=1;continue
    target,matched=matcher.match_or_add(record);record['target_source_id']=target
    counts['matched_existing_or_duplicate' if matched else 'new_listings']+=1
    records.append(record)
report={'release':a.release,'observed_at':observed,'extract_sha256':hashlib.sha256(Path(a.extract).read_bytes()).hexdigest(),
        'boundary_sha256':hashlib.sha256(Path(a.boundary).read_bytes()).hexdigest(),'counts':counts,
        'areas':Counter(r['area'] for r in records if r['target_source_id']==r['source_id']),
        'limitations':'Not a complete census. Confidence >=0.5; exact-name/proximity dedup may miss spelling variants. Unknown operating status is not verified open. No prices inferred.'}
(out/'plan.json').write_text(json.dumps(records,ensure_ascii=False))
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
