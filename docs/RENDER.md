# Deploy the sample app on Render

The root render.yaml provisions one Docker web service containing Next.js and FastAPI, plus a managed PostgreSQL database. Both use the free plan. This is a fictional sample-data demo; simulation is enabled and never counts as verified spending. No paid resource is requested by this blueprint. Review Render's current free-plan limits, database expiry and availability in the confirmation screen. Do not accept an automatic paid upgrade unless you want its cost.

## Launch
1. Sign into https://dashboard.render.com with GitHub.
2. Choose **New → Blueprint**, connect manavv28/restaurant-management-system.
3. Select **deploy/biteai-mvp**, which contains render.yaml.
4. Review the free web service and free database, then launch the Blueprint.
5. Wait for the web service's deployment to succeed. Open the **.onrender.com** address shown by Render.

Render generates JWT_SECRET and wires the database URL automatically. No Gemini, Google Places, Supabase or payment keys are needed to explore the sample app. One hosting account is enough. This demo uses Render PostgreSQL; the documented Supabase deployment remains an alternative.

## Validate
- Open the website and search “Chinese Hakka noodles under ₹300 within 2 km” in Bandra.
- Open the fictional Wok & Wonder listing and inspect the sample menu.
- Register a sample account to try favourites and offers.
- /api/health must report database connected.
- The free web service may sleep when idle and take time to start again.
- Back up or upgrade your database before its free-plan expiry if you want to keep accounts and menus.

## Architecture
Public request -> Next.js on Render's PORT -> private 127.0.0.1:8000 FastAPI -> managed PostgreSQL.
The backend listens on loopback only. The health check goes through Next.js to the database-backed API. The supervisor stops both processes if either exits, allowing Render to restart them. Container runs as a non-root user. .dockerignore excludes .env, local databases and development accounts.

Optional provider keys belong in Render's server environment settings. No gateway is live: /payments/webhook returns 501. Do not enter real payment credentials, PINs or OTPs.

## Local container validation
    docker build -t biteai .
    docker run --rm -p 10000:10000 \
      -e JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
      -e SEED_SAMPLE_DATA=true biteai

Local container SQLite is temporary; the Blueprint uses persistent managed PostgreSQL.
