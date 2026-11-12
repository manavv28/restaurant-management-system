"""Build bounded idempotent SQL batches from a reviewed plan, without credentials.

Run through a PostgreSQL client with transaction support. Existing restaurant
metadata, owned records and all menus are never updated by these statements.
"""
import argparse,json
from pathlib import Path

def batch_sql(records):
    payload=json.dumps(records,ensure_ascii=False)
    tag='$biteai_city_extract$'
    if tag in payload:raise ValueError('SQL delimiter collision')
    source=f"jsonb_to_recordset({tag}{payload}{tag}::jsonb) AS x(name text,address text,area text,latitude double precision,longitude double precision,phone text,website text,pin_code text,cuisine text,source_id text,source text,external_id text,licence text,observed_at text,details text,target_source_id text)"
    return f"""WITH input AS (SELECT * FROM {source}),
inserted AS (
INSERT INTO restaurants (name,address,area,latitude,longitude,phone,website,pin_code,cuisine,source_id,source,sample,updated_at,opening_hours,price_range,image_url,image_attribution,ordering_url,ownership_verified)
SELECT name,address,area,latitude,longitude,phone,website,pin_code,cuisine,source_id,source,false,observed_at,'Unknown','Unknown','','','',false
FROM input WHERE source_id=target_source_id
ON CONFLICT (source_id) DO NOTHING RETURNING id,source_id
), aliases AS (
INSERT INTO catalog_identities (provider,external_id,restaurant_id,source_url,licence,observed_at,details)
SELECT 'overture',x.external_id,coalesce(i.id,r.id),'https://explore.overturemaps.org/?gers_id='||x.external_id,x.licence,x.observed_at,x.details
FROM input x LEFT JOIN inserted i ON i.source_id=x.target_source_id
LEFT JOIN restaurants r ON r.source_id=x.target_source_id
WHERE coalesce(i.id,r.id) IS NOT NULL
ON CONFLICT (provider,external_id) DO UPDATE SET licence=EXCLUDED.licence,observed_at=EXCLUDED.observed_at,details=EXCLUDED.details
WHERE catalog_identities.restaurant_id=EXCLUDED.restaurant_id
RETURNING restaurant_id
)
SELECT (SELECT count(*) FROM inserted) AS inserted_listings,count(*) AS linked_provider_records FROM aliases;
"""


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('output');p.add_argument('--batch-size',type=int,default=250)
    a=p.parse_args()
    if not 1<=a.batch_size<=500:raise ValueError('Batch size must be 1..500')
    rows=json.loads(Path(a.plan).read_text());out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    for start in range(0,len(rows),a.batch_size):
        (out/f'{start//a.batch_size:03d}.sql').write_text(batch_sql(rows[start:start+a.batch_size]))
    print(f'{len(rows)} provider records in {(len(rows)+a.batch_size-1)//a.batch_size} transactional batches')
