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
