# Vercel + Cloud Run + Supabase

Current target: Vercel serves the Next.js frontend, Cloud Run serves FastAPI, Supabase hosts PostgreSQL. The restaurant collector runs as a bounded Cloud Run Job invoked by Cloud Scheduler. No continuous background loop runs inside a scale-to-zero web service.

## What is required
- A Google Cloud project with billing enabled and permission to create Cloud Run, Cloud Build, Artifact Registry, Secret Manager and Scheduler resources.
- Your existing Supabase project. Use a fresh database for automatic migration. No Render records are copied or deleted by these scripts.
- A Vercel frontend project.
Cloud Run has a usage-based free allowance, not guaranteed zero cost. Builds, image storage, jobs, Scheduler, database plans and network usage have separate limits. Review pricing and set billing alerts.

## 1. Store Supabase credentials securely in Google Cloud
In Supabase click Connect, then choose the **Session pooler** PostgreSQL connection string on port 5432. Session mode supports migrations and SQLAlchemy connections. Use the database password, not the Supabase anon or service-role HTTP API key.
URL-encode special characters in the password. Use TLS certificate verification:
    postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@YOUR_SESSION_POOLER_HOST:5432/postgres?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt
Substitute the actual host and username from Supabase; do not guess them. If the project's server certificate is not trusted by the system CA bundle, configure its official CA rather than disabling verification.

In Google Cloud Console → Secret Manager, create:
- biteai-database-url: the complete connection string above.
- biteai-jwt-secret: a random value of at least 32 characters. Generate locally with Python secrets.token_hex(32); store the output directly in Secret Manager.
Never commit these values or send them in chat.

## 2. Deploy from Google Cloud Shell
Open Cloud Shell in your Google Cloud project:
    git clone --branch deploy/biteai-mvp https://github.com/manavv28/restaurant-management-system.git
    cd restaurant-management-system
    export PROJECT_ID=YOUR_GOOGLE_CLOUD_PROJECT_ID
    export REGION=asia-south1
    bash scripts/deploy-cloud-run.sh

Choose a region near your Supabase region if asia-south1 is not suitable. The script:
1. Creates dedicated build/runtime service accounts with scoped storage/repository/secret access.
2. Builds the Python-only image from backend/Dockerfile.cloudrun.
3. Runs a migration job before deploying the API.
4. Deploys the public API with two maximum instances and small database connection pools.
5. Creates collection and retention jobs without schedules.

The migration job applies both SQL files transactionally, records checksums and skips unchanged previously applied migrations. It uses a PostgreSQL advisory lock against concurrent migrations. It does not drop existing records. If your Supabase database already contains BiteAI tables created outside this migration ledger, the first migration fails and rolls back; reconcile that existing schema before retrying rather than resetting it.
Supabase browser roles cannot access the application tables directly: migrations enable RLS and revoke anon/authenticated grants. The current app uses its own FastAPI account system, not Supabase Auth.

The script checks the direct API /health endpoint. If organisation policy prevents public invocation, deployment fails at that permission step; resolve it through your Google Cloud administrator rather than exposing credentials.

## 3. Connect Vercel
Copy the Cloud Run service URL printed by the deploy script.
In Vercel → project → Settings → Environment Variables:
    API_INTERNAL_URL=https://YOUR_SERVICE_URL.run.app
**Do not append /api.** Cloud Run exposes /search and /health directly. (The old combined Render deployment needed a trailing /api.)
Set this for the intended Vercel environments, then redeploy Vercel so its server-side rewrite is rebuilt. Vercel /api/health should return database connected.

## 4. Run and schedule restaurant collection
Try one bounded execution:
    gcloud run jobs execute biteai-collect --region="$REGION" --wait

If sources are unreachable the job fails and catalog_jobs retains the retry/error; it does not create fake records.
For recurring hourly collection and daily retention:
    bash scripts/schedule-cloud-run.sh

The scheduler uses OAuth and a dedicated invoker account. Schedule times use Asia/Kolkata. Jobs share the API's Supabase database. A small initial collection covers five Mumbai area circles only, not all Mumbai restaurants.
A free Supabase project may pause under its current inactivity policy. Cloud Run scale-to-zero can still have a cold start; this migration does not promise instant responses.

## Optional source integrations
Configure APPROVED_MENU_HOSTS on both API and collection job for exact restaurant website hosts that you permit.
For Gemini parsing/extraction, create a Secret Manager secret and bind GEMINI_API_KEY to both API and collection job. Provider keys are not provisioned by the scripts. The helper uses additive environment/secret updates and preserves additional existing bindings on redeploy.
Do not enable real Razorpay orders without merchant approval, hosted checkout, settlement/routing and reconciliation. See PAYMENTS.md.

## Data migration and cutover
A new Supabase database does not contain existing Render accounts or restaurant records. If those matter, perform a reviewed pg_dump/restore or data-only import before switching. Do not stop/delete Render until the Cloud Run API and Vercel journeys pass against Supabase. The existing Render service remains untouched by these scripts.

## Troubleshooting
- Migration job failed: inspect Cloud Run Job logs. Existing schema conflicts, invalid database URL, paused Supabase, TLS trust and database privileges are distinct causes.
- Cloud Run startup failed: check JWT secret length, completed migrations, PostgreSQL connectivity and required secrets.
- Vercel search failed: check API_INTERNAL_URL has no trailing /api and redeploy after changing it.
- Worker didn't run: a Cloud Run service is not a scheduler; execute/schedule the collection job.
