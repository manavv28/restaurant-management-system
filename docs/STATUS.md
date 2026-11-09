# Current development status

The original demo status below describes the first release. This update adds:
- Durable collection jobs, retries, crash recovery and an optional supervised worker.
- OpenStreetMap discovery and deduplication with source attribution.
- Approved-source menu extraction using Schema.org and optional evidence-checked Gemini extraction.
- Price evidence/expiry, stale-price exclusion, price-change audit and stored search-match snapshots.
- Coverage and unknown-price UI, owner source registration and job inspection.
- Razorpay order/signature/capture adapter, disabled until credentials and merchant onboarding.

Validation: 23 backend tests, four browser journeys, frontend build. Provider responses in tests are fixtures.
A real discovery attempt was blocked by the workspace proxy and recorded as a retry. No live Mumbai dataset has been populated here. Gemini and Google Places keys are absent. Collection still needs network access and approved website sources.
Live payment checkout UI, settlement/routing, refunds and provider/merchant approval remain incomplete. No live funds were moved.
No new production deployment has been performed during this update.

## Original demo baseline (historical)

Implemented locally:
- Next.js responsive consumer search/list/map/menu experience and browser voice adapter (text fallback).
- FastAPI relational database service; local SQLite is persistent across restarts.
- Registration/login, customer/owner roles, ownership checks, profile/cuisine preferences.
- Restaurant/dish favourites, private history, history deletion, consent and GPS clearing.
- Structured Gemini adapter and visible local-rule fallback; deterministic price/distance filtering and preference-aware ranking; persisted search execution traces.
- Explicitly fictional samples across Bandra, Andheri, Dadar, Powai and Colaba.
- Owner listing/details/menu editing, permission-confirmed bulk menu ingestion, name normalization, duplicate merging and price-change logs.
- Google Places discovery adapter with no inferred prices and no permanent provider metadata cache.
- Campaign creation, search/spend/visit eligibility, order minimum/cap/validity/limits, reservation audits.
- Consent-gated transaction simulation excluded from verified spending; live webhook fails closed.
- Aggregate search/cuisine/dish/area metrics and per-owner engagement/reservation analytics.
- Daily retention job, PostgreSQL/Supabase initial schema and RLS, setup/deployment documentation.
- Backend tests and desktop/mobile browser journey tests.

External/deferred:
- Live Supabase, Gemini and Google Places require service configuration and credentialed validation. Current validation uses SQLite and local parsing.
- The interactive map uses Leaflet/OpenStreetMap tiles, a working key-free alternative; Google Maps rendering is not implemented. Google Places is a separate optional backend integration.
- Voice API depends on the user's browser and microphone access; automated testing exercises text.
- Menu ingestion accepts authorised structured exports; arbitrary web/PDF extraction, autonomous scheduled collection and broad Mumbai data coverage are not implemented.
- Payment gateway signature adapter, real settlement and live financial data integrations are not implemented.
- Analytics expose independent searches/clicks, not a misleading attributed conversion rate; attribution/funnels require additional event modelling.
- Hosting/public deployment, Supabase live migration and production security hardening have not been performed.

## Selected hosting target
Supabase PostgreSQL + Cloud Run FastAPI + Vercel frontend. Deployment scripts and a separate scheduled-job configuration are available in SUPABASE_CLOUD_RUN.md. Local container/PostgreSQL validation passed; actual hosting and database cutover await Google Cloud project setup and secure credentials. Existing Render resources remain unchanged.

## Current hosting decision
Keep the existing Render Free backend and use Supabase Free for PostgreSQL; do not provision Google Cloud resources. render.yaml now requests a manually supplied DATABASE_URL instead of a Render database reference. The legacy Render database definition is retained to protect existing data until a verified transfer/cutover.
See RENDER_SUPABASE.md. No real credentials were available, no live transfer was attempted, and no existing hosting resources were modified.
