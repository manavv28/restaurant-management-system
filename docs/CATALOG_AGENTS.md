# Source-backed catalog and collection agents

This release builds the missing collection workflows. It does not claim a complete Mumbai database or that a failed provider request returned real data.

## Operator workflow
From backend, with the same DATABASE_URL as the API:
    ../.venv/bin/python -m app.catalog_worker --seed-osm --schedule --once

For hosted installations use python -m app.catalog_worker with the same arguments.
--seed-osm registers five OpenStreetMap Overpass discovery sources: 3 km around Bandra, Andheri, Powai, Colaba and Dadar. These circles are a partial dataset, not a Mumbai-wide census. It registers jobs, not fictional restaurant records.
--schedule queues due enabled sources and prevents duplicate active jobs. Failed sources receive a six-hour cooldown after three attempts.
--once claims and runs one available job. Repeat to drain batches (five initial jobs need five invocations). Exit code 1 means failure/retry, not readiness.
Run the command with --schedule --once every minute from a platform scheduler or worker. The production supervisor starts the polling worker when CATALOG_WORKER_ENABLED=true; the updated Render blueprint enables it. Existing deployments need that environment variable and a new deployment. It polls every 30 seconds. Free-service sleeping suspends collection too; use a separate persistent worker for reliable schedules. Do not schedule --seed-osm repeatedly as a substitute for collecting jobs. No paid worker is provisioned.

Jobs persist attempts, a ten-minute crash lease, exponential retry delays, terminal failures and structured tool traces. Sources refresh based on last successful check. An HTTP failure does not create restaurant rows.

## OpenStreetMap discovery
Only the configured Overpass endpoint is queried. Named restaurant nodes/ways/relations inside the Mumbai bounding box are deduplicated by stable OSM type/ID. Stored fields include community-supplied coordinates, address, cuisine, published phone and website when present. Missing values stay missing. Ratings and menus are never inferred.
Attribute © OpenStreetMap contributors, ODbL. Review ODbL attribution/share-alike obligations before distributing derived databases. Cross-provider entity merging is not implemented; stable OSM IDs prevent duplicate discovery imports.

## Menu agent
The operator sets APPROVED_MENU_HOSTS to exact approved restaurant website hosts. Owners register URLs and their permission basis in the restaurant portal. URLs must use HTTPS without credentials, custom ports or IP literals. No redirects or unapproved hosts are followed. Robots is checked (404 means no rules; denial/other errors block collection). Responses are size bounded. No restricted platform scraping.
The worker extracts Schema.org MenuItem+Offer records with explicit INR prices. If none exist and Gemini is configured, it extracts candidates from visible page text and checks exact name/evidence spans and rupee amounts. Conflicting prices and evidence-free candidates are rejected.
This is source observation, not independent verification. Evidence includes URL, collection time, content hash, extraction method and expiry. Raw pages are not retained indefinitely. An extraction refresh updates prior machine-imported items for the same source and records old/new prices; owner entries are not overwritten. Missing source items are deactivated. Failed/empty extractions preserve last-known evidence until original expiry; stale items cannot satisfy a search budget.
Changing an item manually detaches machine evidence, so future collection does not overwrite that owner entry.

## Search and data lake
Searches persist matched restaurant/item IDs, source, price and distance snapshots, plus their workflow trace. Deleting search history cascades to these snapshots. Catalog coverage reports real listing count separately from fictional samples and fresh source menu counts. Real nearby listings without a fresh menu are shown separately as unknown prices and never claimed as budget matches.

## Access required for live collection
- overpass-api.de must be allowed by the cloud network.
- Each approved restaurant website must be both operator-authorised and network-allowed.
- Optional AI extraction/search: GEMINI_API_KEY plus generativelanguage.googleapis.com.
- Existing optional Places discovery: GOOGLE_PLACES_API_KEY plus places.googleapis.com. Places metadata is not silently persisted as an unrestricted data lake.
At implementation time a real Overpass request returned HTTP 403 and both API keys were absent. No successful live catalog population is claimed. Unit/provider tests use labelled fixture data in an isolated test database.
