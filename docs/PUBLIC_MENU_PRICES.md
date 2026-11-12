# Public menu price collection

IndiaRestros explicitly permits personal and commercial API use in its [terms](https://indiarestros.com/terms). Its [documented API](https://indiarestros.com/api/docs) publishes INR menu facts and a 120-request/minute/IP limit. The offline collector makes serial requests at 90/minute by default, capped at 100, and honors Retry-After. No account, API key, paid service, photographs, reviews or publisher descriptions are needed.

Only venues inside the Mumbai City/Suburban boundary are considered. Matches require an exact normalized name within 80 metres, or matching phone and brand within 150 metres; ambiguous branches are rejected. The original menu URL is checked for conflicting brand/area names. One provider record is selected per existing venue, preferring the newest original observation. This cannot guarantee complete coverage or restaurant-confirmed prices.

Only positive, unambiguous INR prices are accepted. Conflicting duplicate names, variants, ranges, other currencies, unknown observation dates and observations older than 90 days require review. Original source dates, links, delivery context, retrieval timestamps and response hashes are retained. Evidence expires after 48 hours or 90 days from the original observation, whichever comes first. The UI identifies these as third-party listed prices and asks users to confirm the current price. Delivery prices can differ from dine-in prices; fees and taxes may differ.

Existing publisher menus, owner-managed restaurants and owner menu items are protected. Stable source keys make replay idempotent. Atomic batches publish items, evidence and audit metadata together; missing items are withdrawn on refresh. A partial unique index permits one API feed per restaurant. Paused feeds stay paused. Publication stops at a 425 MiB database budget, leaving headroom below the Supabase Free limit. Do not increase paid infrastructure automatically.

The existing Render Free worker refreshes due sources after 24 hours, at most five successful API menus per 30-second loop. HTTP 429 delays all pending API jobs until Retry-After. Free instances can sleep; this is not an always-on freshness guarantee. Render remains the backend and Supabase remains the database.

## Reproduce a reviewed import

Use a local virtual environment with backend requirements and `scripts/catalog/public-menu-requirements.txt`. Export canonical restaurant records with `source_id`, name, latitude, longitude and optional phone to JSON. These are input facts, not credentials.

```sh
PYTHONPATH=backend python scripts/catalog/collect_public_menus.py \
  --catalog canonical-restaurants.json \
  --boundary scripts/catalog/mumbai-boundary.geojson --output work/public-menus
PYTHONPATH=backend python scripts/catalog/prepare_public_menus.py \
  --snapshots work/public-menus/menus --output work/reviewed-menu-plan
```

Collection checkpoints after every page and can resume. Review the generated report and immutable plan before executing its bounded SQL batches. Apply `20261112180527_public_menu_price_keys.sql` first and deploy the compatible worker before enabling feeds. Rehearse imports, replay, preservation and search against an isolated database. Verify production counts and a real supervised refresh after publication. Saved public snapshots and generated SQL remain local work artifacts, outside Git.
