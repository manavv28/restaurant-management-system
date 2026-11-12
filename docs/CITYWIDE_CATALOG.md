# Mumbai catalog expansion

The 12 November 2026 expansion uses Overture Maps Places release **2026-10-21.0**, selected through its spatial STAC index and downloaded anonymously from the public S3 dataset. No paid service or API key was used. Render remains Free and Supabase remains the database.

[Import report](catalog/mumbai-2026-11-12-report.json) records source/boundary hashes, exclusions and search-area counts. The bounding extract contains 193,524 places. Of 16,738 food-category candidates, 1,660 fall outside Mumbai City / Mumbai Suburban district polygons. Filtering excludes 4 known closures, 261 non-eatery categories and 4,658 low-confidence records. 10,155 qualified provider records become 10,026 new listings plus 129 matches to existing or duplicate records. Existing restaurant IDs and menus are preserved. This does not clean up pre-existing OSM duplicates.

This is **not all restaurants in Mumbai**. Missing venues, spelling duplicates, stale businesses and category errors remain possible. Source confidence ≥0.5 is an inclusion rule, not verification or a rating. Unknown operating status stays unknown. Geographic scope excludes Thane and Navi Mumbai. Search areas are nearest-centre buckets, not official wards. Restaurants, cafés, bakeries, fast-food outlets and other eateries are included; groceries, internet cafés, candy stores and chocolatiers are excluded. No menu, price, star rating or opening hours are inferred.

## Reproduce

Use an isolated operator virtualenv with `scripts/catalog/requirements.txt`; these large extract dependencies are deliberately absent from the backend image. Python tools preserve the session HTTPS proxy and certificate trust and use anonymous public S3 access. STAC lookup failures abort rather than scanning the worldwide dataset.

```sh
python scripts/catalog/download_overture.py --release 2026-10-21.0 --output work/mumbai-expansion
PYTHONPATH=backend python scripts/catalog/prepare_mumbai.py \
  --extract work/mumbai-expansion/overture-bbox.jsonl \
  --boundary scripts/catalog/mumbai-boundary.geojson \
  --existing work/mumbai-expansion/existing.json \
  --output work/mumbai-expansion --release 2026-10-21.0
python scripts/catalog/build_import_sql.py work/mumbai-expansion/plan.json work/mumbai-expansion/sql
```

`existing.json` is an operator export of public restaurant fields (`id,name,latitude,longitude,phone,source_id,owner_id`), not accounts or credentials. Review the report and plan before executing generated SQL batches through an authenticated database client. Apply the additive `catalog_identities` migration first. Each batch is transactional and replayable; inserts conflict safely on source ID and never overwrite existing restaurant metadata or menus. Provider aliases retain licence, release, taxonomy, confidence and original source records. Matching uses exact normalized name within 80 metres; distinct branches farther away remain separate. Ambiguous spelling variants remain separate for review.

After import verify restaurant/alias counts, foreign keys, duplicate source IDs, owner/menu preservation, area coverage and query plans. Replays do not refresh menus or imply a newer source release. Future updates must handle changes in provider IDs and review possible closures before replacing existing data.

## Sources and licences

- [Official getting-data guide](https://docs.overturemaps.org/getting-data/) and [Places schema](https://docs.overturemaps.org/schema/reference/places/place/).
- [Overture attribution](https://docs.overturemaps.org/attribution/): Meta, Microsoft, PinMeTo, DAC, Uberall and Overture processing provenance use [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/). AllThePlaces uses [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- Foursquare: Copyright 2024 Foursquare Labs, Inc. All rights reserved. [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0); transformed to Overture schema, changed 2026-03-18. [NOTICE.txt](https://opensource.foursquare.com/places-notice-txt/). BiteAI further filtered and normalized the data.
- Boundary geometry and existing OSM listings: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). District relations [7964376](https://www.openstreetmap.org/relation/7964376) and [7964375](https://www.openstreetmap.org/relation/7964375), retrieved once through Nominatim. No Google search or Maps pages were scraped.

Public attribution is also available on `/data-sources`.

## Verified production result

The live catalog has **10,404 listings across 48 search areas**, with 10,155 linked Overture identities and all 91 existing Hakkasan menu items preserved. Database size after import was 39 MB. [Production evidence](catalog/mumbai-2026-11-12-production.json) includes the release, deployments, migration checksum, batch results and test references. Both public origins serve the directory and full licence notices.
