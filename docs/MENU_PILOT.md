# Bandra menu-source pilot — 12 November 2026

Ten existing catalog listings were checked through web search and their independently published restaurant pages. This is a small feasibility pilot, not complete neighborhood coverage. The current Google Places API key is unconfigured, so no credentialed Places/photo request or paid Google resource was used.

Results are recorded in [menu-pilot-results.json](menu-pilot-results.json), with the reproducible source manifest in [menu-pilot-bandra.json](menu-pilot-bandra.json). Initial observation: one restaurant has 91 unambiguous, explicitly marked INR dine-in dish prices; the other nine have no publishable priced menu from the checked sources. Keep those nine unpriced until evidence becomes available.

| Restaurant | Pilot result |
|---|---|
| Hakkasan Mumbai | 91 explicit prices in the official Mumbai A La Carte section. Other menus, wine and delivery prices are excluded. |
| Meraki | Listed official website returns 404. |
| Goh Jia Ting | Existing website points to Bora Bora, a different restaurant brand. No menu attached. |
| Ray's Cafe & Pizzeria | Official page links to a PDF named February 2025. Extracted text is for review; date/portion/price evidence is incomplete. |
| Elco | Official menu lists dishes without prices. |
| Jai Jawan | Bandra menu link is a coming-soon image; linked Khar/Andheri PDFs are different branches. |
| Sahibaan | Checked official site has no usable priced menu. |
| Yugo Sushi | Listed website unavailable; unrelated foreign namesakes were rejected. |
| Gracias Granny | Official page checked, without branch-specific price evidence. |
| Banana Leaf | The broad OSM area bucket includes a Juhu address; branch identity needs review. |

## Collection and import behavior

The existing catalog worker now understands explicit publisher HTML menu cards in addition to schema.org. It requires an explicitly declared INR food/dine-in section, a single dish title and a single unambiguous price. Conflicting duplicate prices, ranges, multiple variants, foreign currencies and unrelated numeric text are omitted. Evidence records contain the source URL, source hash, method, observed time and expiry. Existing price-change audits and source pause/refresh controls apply. Owner menus are not overwritten.

PUBLISHER_MENU_HOSTS extends the existing APPROVED_MENU_HOSTS list without replacing it. Only exact HTTPS hosts explicitly configured by the operator are fetched. Robots rules, response-size limits and redirect rejection remain enforced. Public publisher collection does not claim restaurant ownership or legal merchant verification.

PDF and image inspection is available through `python -m app.menu_pilot`. Native pdftotext/Tesseract work is bounded by input size, memory, CPU, output size and wall-clock time. Text extraction covers at most ten PDF pages; image-only PDFs can OCR the first page. PDF/image output remains review-only and is never automatically turned into live prices. No menu images are republished.

Google Maps is not a bulk menu feed. [Google's current Places policy](https://developers.google.com/maps/documentation/places/web-service/policies) restricts scraping, storage and derived content. Accordingly, Google is used for discovery/link lookup where available; this implementation does not harvest Maps photos into a permanent price catalog. A Google Places key alone does not resolve menu-image reuse or provide structured dishes/prices.

## Reproduce the inspection

In an isolated environment with backend dependencies and native poppler/Tesseract tools installed:

```sh
APPROVED_MENU_HOSTS=taogroup.com,img1.wsimg.com,www.elcorestaurants.com,jaijawanfoods.com,www.sahibaan.com,graciasgranny.com \
PYTHONPATH=backend python -m app.menu_pilot \
  --manifest docs/menu-pilot-bandra.json --output /tmp/menu-pilot-results.json
```

The CLI writes a review report only and does not modify the database. Native inspection runs serially for the Render Free memory budget. The existing supervised catalog worker performs publication only for the explicitly approved HTML source. No schema migration is needed for this feature.

## Live pilot and refresh limitation

Initial pilot release `fd55f5415473` was deployed on the selected Vercel frontend and Render Free backend. The current verified release is `a47fa39aae36dc9ae4319e6db5da934e51afea02`. The reviewed publisher source is registered as source 6 for restaurant 24. Its direct Render fetch returned HTTP 403 (provider job 31); that failure remains visible and was not reported as a successful automated refresh.

A fresh public-source inspection through the managed workspace retrieved the same official menu normally, with robots checks and no access challenge bypass. Its 91 validated price observations were imported as a separate operator snapshot (job 32, audit 1), retaining the actual content hash, observed time and 48-hour expiry. The snapshot contains facts only; publisher descriptions and menu images are not republished. Both live API origins returned all 91 menu items and a real Chinese-under-₹1500 budget match, with a fresh-source label. The nine remaining restaurants were left unpriced.

Automatic refresh from Render remains unverified because of the publisher's HTTP 403. The target refresh interval is 24 hours while the Free service is awake; the snapshot is not kept artificially fresh if collection fails. Its prices expire from matching after 48 hours without a successful refresh. Current snapshot timestamps/hash and both job IDs are recorded in the results JSON. This pilot does not establish automatic coverage for every restaurant or Google Maps photo ingestion.

## Validation

Initial local PostgreSQL suite: 72 passed. Hosted pilot CI run 43188463058 passed 71 tests with one native-PDF test skipped because the hosted runner lacks pdftotext; the native-PDF test passed locally. All 14 browser journeys, production frontend build, Docker build and non-root image smoke passed. Release integration run 43189179162 and live public-browser run 43189179394 passed. No database migration was required.

Live-data checks exposed redundant queries per dish and an inaccurate owner-supplied search explanation for publisher prices. The follow-up batches evidence, chooses the best dish before loading restaurant offers/details, and labels published-menu observations correctly. A 90-dish regression check bounds search reads and restaurant-menu reads; the updated local PostgreSQL suite passes 73 tests.

## Final public verification

Current release `a47fa39aae36` is live on Render Free and the selected Vercel project. Both public origins returned all 91 fresh source observations and the exact query “Find spicy jackfruit dumpling under ₹1000 within 2 km in Bandra” matched Hakkasan’s Spicy jackfruit dumpling at ₹595, with the published-menu explanation. Menu retrieval is batched rather than issuing one evidence query per dish. Existing email configuration remains enabled; Supabase verify-full TLS is unchanged.

[Final integration run 43191707994](https://github.com/manavv28/restaurant-management-system/actions/runs/43191707994) and [final live-browser run 43191707700](https://github.com/manavv28/restaurant-management-system/actions/runs/43191707700) passed. The follow-up CI passed 72 PostgreSQL tests with one native-PDF test skipped on the runner, all 14 browser journeys, frontend build, production Docker build and non-root database-backed smoke. Local PostgreSQL ran all 73 tests, including native PDF extraction. No schema migration was introduced.

Snapshot observation: 12 November 2026, 14:46 IST; expiry: 14 November 2026, 14:46 IST unless refreshed. The successful operator snapshot and failed Render provider job remain distinct. Automatic refresh and all-restaurant menu coverage are still unverified.
