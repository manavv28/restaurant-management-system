# Validation evidence
- Repeatable scripts/setup.sh completed: Python dependencies, npm ci, Next.js production build and 11 backend tests.
- TypeScript typecheck passed.
- Three Playwright Chromium journeys passed: search/menu/account/favourites/consent simulation; mobile overflow/map marker interaction; owner listing/menu/campaign creation.
- After the final map warning/accessibility changes, production build and mobile/map browser test passed again.
- scripts/dev.sh starts the current backend and frontend; backend and same-origin frontend proxy health checks respond successfully.
- Running search smoke query returned one fictional Hakka noodles sample priced at ₹240 within 2 km of Bandra.
- Git diff whitespace check passed.
- Browser tests used an isolated /tmp SQLite database; the final development server uses a clean ignored local demo database.
- Backend tests report one upstream Starlette/AnyIO deprecation warning; no failed/skipped tests.
- Live Supabase, Gemini, Google Places and payment providers were not tested. Google Places/Gemini keys are absent.
- Map tile HTTP requests receive a cloud-network 403; marker interaction is verified and the UI explains missing street tiles.
- Reusable cloud configuration draft persistence could not be confirmed due to an INVALID_ARGUMENT tool error. Repository scripts are saved; publication/deployment was not performed.

## Deployment package validation
- Docker multi-stage production image built with TLS/package signature checks enabled.
- Image started as a non-root user against an isolated PostgreSQL 16 container using Render-style postgres:// URL normalization.
- /api/health passed through the production Next.js server to the database.
- All three Playwright journeys passed against this production container with PostgreSQL.
- Local validation used host port 10081; port 10080 is blocked by Chromium and is not used in deployment.
- Initial container launch raced database startup; after PostgreSQL readiness passed, restarting the app succeeded. Render should provision its database before launching the web service.
- Live Render creation remains blocked by missing account authentication and the cloud network's HTTP 403 for api.render.com.


## Catalog / source agent update
- 23 backend tests passed (including source permissions, OSM fixture import/dedup, extraction, conflicting prices, stale exclusion, retries, source evidence validation, search snapshot deletion, webhook HMAC and replay).
- Four Playwright journeys passed against the running FastAPI/Next.js app, including coverage honesty and unapproved-source rejection.
- Next.js production build passed.
- An actual worker run registered five OSM sources, queued five jobs and recorded a retryable ProxyError on the first source. No restaurant rows were invented or imported on failure.
- Keys for Gemini and Google Places are absent. Live provider behaviour and actual source population remain unverified.

- The production container built successfully with the new code.
- Applied migrations 001 and 002 to a fresh PostgreSQL 16 database with ON_ERROR_STOP enabled; both passed.
- Started the production supervisor with CATALOG_WORKER_ENABLED=true. API/database health passed, coverage reported five registered discovery sources and zero successfully collected real listings.

## Supabase / Cloud Run configuration
- 26 backend tests passed, including production refusal of SQLite, pre-migration startup failure and bounded collection runs.
- Backend-only Cloud Run image built successfully.
- Migration runner applied 001 and 002 to PostgreSQL 16, then ran again successfully without reapplying them.
- The image served /health and /search on PORT 8080 against that database with sample creation disabled.
- Both deployment helper shell scripts passed bash syntax checks.
- Google Cloud deployment/build/scheduler commands have not been run against a real project. No Google Cloud identity is connected and a billing-enabled project has not been provided.
- Live Supabase connectivity/TLS, data transfer from Render, Cloud Run deployment, Scheduler invocation and Vercel cutover remain unverified. The existing Render service/database were not modified.

## Render → Supabase preparation
- Existing 26 backend tests passed.
- transfer_postgres was exercised against two isolated PostgreSQL 16 databases with fixture accounts, menus and favourites.
- Audit mode copied no rows. Copy mode preserved IDs, password hashes, foreign keys and row hashes; generated ID sequences advanced correctly.
- A second transfer into a nonempty destination was refused; the source remained unchanged.
- Validation used fixtures only. Live Render/Supabase data, credentials and connectivity were not available.

## Supabase certificate troubleshooting
A live Render screenshot reported certificate verification failure with the system CA bundle. Supabase's official SSL documentation requires its downloaded database CA for verify-full. RENDER_SUPABASE.md now uses a Render secret-file mount at /etc/secrets/supabase-ca.crt. The live certificate upload and reconnection remain user actions and have not been verified here. Certificate/hostname verification remains enabled.

## Missing Supabase certificate file fix
- The reported failure was a missing /etc/secrets/supabase-ca.crt, after earlier system-store certificate verification failure.
- 36 backend tests passed. Added credential-preservation, legacy-path recovery, explicit CA, malformed/missing CA, lookalike-host and bundle-validation coverage.
- Built the full deployment container with an explicitly labelled generated test CA. Production and fixture/operator certificate sources use separate build-cache keys.
- Started PostgreSQL with a certificate signed by that fixture CA and a SAN matching the isolated test alias for the Supabase pooler.
- The non-root app connected using verify-full while the old Secret File path was absent; encoded @ credentials were preserved.
- Connections using the wrong hostname and an untrusted root store were rejected. The final image's proxied /api/health passed.
- Official production CA URL was confirmed from the official Supabase Studio source. The workspace proxy blocks that S3 host, so the production CA bytes and a live private Supabase connection could not be tested here. Render's production build fetches that CA over verified HTTPS and validates it before installing.
- Fixture certificates/images are local tests only; no fixture certificate is committed, included in default production build context, or deployed.

## Public menu price release — 13 November 2026 (India)

Release `abae206e042a` is live on the selected Vercel frontend and Render Free backend, with Supabase verify-full TLS. The complete public source scan checked 54,422 listings and saved 2,795 menu snapshots. Source-date, identity and price checks rejected 181 menus; the published plans select one API feed for each of 2,612 venues. Production now has 357,603 new third-party price facts plus all 91 preserved publisher prices: 357,694 total, across 2,613 of 10,404 real-source listings. Every price has active evidence; no API item is missing evidence, and no samples were added. Database size was 286,365,363 bytes, below the 425 MiB publication guard.

Both isolated staged imports passed replay and publisher-preservation checks. A real Render refresh succeeded on attempt one (job 76). All 87 local backend tests passed; hosted CI passed 86 with one native-PDF-only skip, 24 browser checks, frontend/Docker builds and image smoke. Release integration and live-browser runs 43286798643 / 43286798536 passed. Additional public checks verified menu dates, source links, exact paise, budget/radius bounds, directory pagination, explicit search recovery and no mobile overflow. The final full-data mobile check displayed both counts and opened a newly imported venue with 30 dated reference prices. Two preliminary managed browser bridge requests timed out; the final check passed without network/page errors, with TLS validation enabled throughout. Final public search requests varied from 3.6 to 18.7 seconds; constant low latency on Free hosting is not claimed.

The final source dates range from 9–18 October 2026. These are dated third-party listing observations, not current restaurant-confirmed quotes. Coverage remains partial, and some searches correctly return no priced matches. Full counts, source rejects, hashes, rehearsal evidence and production verification are in [the price report](catalog/menu-prices-2026-11-13.json). The Render error-log check after the release returned no ERROR/Traceback entries.
