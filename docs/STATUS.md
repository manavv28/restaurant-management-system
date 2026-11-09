# MVP delivery status

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
