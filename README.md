# BiteAI · Mumbai food discovery

A working development MVP with Next.js/TypeScript/Tailwind, Python/FastAPI, relational persistence, structured food search, owner portal and auditable personalised rewards.

**Data honesty:** included restaurants and menus are fictional samples, clearly labelled. There is no complete Mumbai dataset, independently verified menu pricing, live ordering, or live payment integration. Owner supplied records remain unverified. No external API success is simulated.

## Deploy the sample app

See [Render deployment](docs/RENDER.md) for a single-account Blueprint with a web app and managed PostgreSQL. The root Dockerfile packages both services. No paid plan is requested; review current Render free-tier limits before launching.

## Run locally
Requires Node.js 20.9+ and Python 3.12+.

    bash scripts/setup.sh
    cp .env.example .env
    # Optional: set a stable random JWT_SECRET and provider keys in .env.
    bash scripts/dev.sh

Open http://localhost:3000 **on the machine running the application**. FastAPI docs: http://localhost:8000/docs. In a cloud workspace these are internal addresses; view through a supported shared browser/desktop or run locally. This repository does not create a public hosted URL.

Choose Bandra and search **“Chinese Hakka noodles under ₹300 within 2 km”**. Open Wok & Wonder to inspect the sample menu. Select other areas for more sample listings. Text works everywhere; browser speech recognition requires browser support, microphone permission and a secure context (or localhost).

Register as a food lover for favourites, history, rewards and consent controls. Make five signed-in searches to unlock a sample 5% campaign. Reserve an offer with an eligible order value. Reservations are not purchases. Simulation is opt-in and never contributes to verified spending.

Register a separate restaurant owner account to create your listing, enter menus/prices, edit details, bulk-import approved JSON menus and create campaigns. Only your own restaurants are editable. New listings appear in search once they have available matching menu items.

## Checks
    PYTHONPATH=backend .venv/bin/pytest backend/tests -q
    npm --prefix frontend run build
    npm --prefix frontend run typecheck

With both services running:
    cd frontend
    CHROMIUM_PATH=/usr/bin/chromium npx playwright test

If Chromium is unavailable, install Playwright Chromium and set CHROMIUM_PATH to its executable. Browser tests create explicitly named test accounts/listings in the running development database; run against an isolated test instance for a clean demo. Do not run them against production.

## Configuration
See [.env.example](.env.example). No API keys are needed for local sample mode. Without a stable JWT_SECRET, restarting the backend signs everyone out.

- DATABASE_URL: defaults to SQLite in the backend working directory. Supabase uses postgresql+psycopg://… with sslmode=require, from secure server environment settings.
- GEMINI_API_KEY and GEMINI_MODEL: optional structured intent extraction, with visible local fallback on failure.
- GOOGLE_PLACES_API_KEY: optional Places API (New) text search in owner portal. Enable API/billing and restrict key. Does not supply menus/prices.
- SEED_SAMPLE_DATA=false: disable fictional seed creation in a fresh real database. Does not delete existing samples.
- ENABLE_PAYMENT_SIMULATION=false: disable simulation.
- APP_ENV=production: requires a configured JWT_SECRET of at least 32 characters.
- CORS_ORIGINS: exact comma-separated frontend origins.
- API_INTERNAL_URL: server-only backend URL used by Next.js rewrites; set before frontend build.

## Deployment
See [deployment guide](docs/DEPLOYMENT.md). Supabase SQL migration is under supabase/migrations. Backend schema can also initialize a fresh database automatically. SQLite has been exercised locally; a live Supabase deployment and external providers require separate credentialed validation.

See [architecture](docs/ARCHITECTURE.md) and [implementation plan / remaining production gates](docs/IMPLEMENTATION.md). This is a demonstrable MVP, not a production-ready payment or restaurant verification system.
