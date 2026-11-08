# Deployment guide

## Supabase / PostgreSQL
1. Create a Supabase project. Keep the database password/connection string in backend secret settings.
2. Apply supabase/migrations/001_initial.sql once to a fresh database using the SQL editor or a migration runner. Existing databases need a reviewed migration, not table resets.
3. Use a server-only postgresql+psycopg:// connection URL. Require TLS (sslmode=require). URL-encode password special characters. Use Supabase's session pooler when IPv4 connectivity requires it.
4. RLS blocks browser roles. Custom FastAPI authentication owns authorisation; do not expect Supabase Auth JWTs to work here.
5. PostGIS is optional for this MVP: distances use deterministic Haversine calculations. Migration includes a coordinate index; add an approved geography index/SQL distance query when scaling.

## Render backend
Root directory: backend. Build: pip install -r requirements.txt
Start: uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
Health path: /health
Set DATABASE_URL, JWT_SECRET (random, >=32 chars), APP_ENV=production, SEED_SAMPLE_DATA=false, ENABLE_PAYMENT_SIMULATION=false, CORS_ORIGINS=https://your-frontend-domain.
Optional: GEMINI_API_KEY, GEMINI_MODEL, GOOGLE_PLACES_API_KEY.

Never use ephemeral SQLite storage for a hosted deployment. Add platform rate limits, monitoring, backups and ownership review before public launch. An owner account can publish only unverified data; self-registration does not verify a real business.

## Vercel frontend
Root directory: frontend. Framework: Next.js. Build: npm run build.
Set API_INTERNAL_URL=https://your-render-backend before build. Only server code uses it.
Next.js rewrites /api/* to the backend, avoiding browser CORS configuration for normal use.
Never place JWT_SECRET, provider keys or DATABASE_URL in NEXT_PUBLIC variables.

## Jobs
Schedule daily with the same backend environment:
    cd backend && python -m app.jobs

The implemented scheduled job is retention. Google discovery is on-demand; menu refresh uses permission-confirmed imports, not unsupervised scraping. Automatic scheduled provider ingestion requires licence/retention design and provider access.

## Live payment integration gate
/payments/webhook deliberately returns 501. Before live enablement, choose an authorised gateway, verify raw-body webhook signatures, match merchant/user consent, process provider event IDs idempotently and record only necessary references/verified amount summaries. Simulated records must never be upgraded to verified by the browser. Never collect UPI PINs, OTPs, passwords or GPay credentials.

## Release validation
Run backend tests, build/typecheck, isolated Playwright journeys, then credentialed Supabase/Gemini/Places tests. Verify TLS, RLS, role boundaries, real data freshness/attribution, consent withdrawal, gateway event replay, backups and recovery. No deployment or publication has been performed by this repository.

## Cloud network destinations
The current cloud network denies OpenStreetMap tile requests (observed HTTP 403). Add a.tile.openstreetmap.org, b.tile.openstreetmap.org and c.tile.openstreetmap.org to the environment's existing outbound allowlist to enable the street basemap. Do not replace unrelated allowed domains. Markers remain functional and the UI reports tile failures.
Optional provider calls also need generativelanguage.googleapis.com and places.googleapis.com when their integrations are configured. Package installation uses registry.npmjs.org, pypi.org and files.pythonhosted.org.
