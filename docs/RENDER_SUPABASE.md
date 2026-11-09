# Keep Render Free; move the database to Supabase Free

Target: Vercel frontend → existing Render FastAPI/Next.js service → Supabase PostgreSQL.
No Google Cloud project or billing is needed. Cloud Run scripts remain optional alternatives and are not run.
Render still sleeps on its free plan. Supabase has its own free-plan quotas/inactivity rules; this does not make background collection always-on.

## 1. Prepare Supabase
In your existing Supabase project open SQL Editor. On a fresh application schema, run these files in order:
- supabase/migrations/001_initial.sql
- supabase/migrations/002_catalog_agents.sql

These create application tables, indexes and RLS restrictions. If BiteAI tables already exist, do not drop them to make migration pass. Inspect the existing schema first.
Open Connect → Session pooler and copy the PostgreSQL connection string on port 5432. Use the database password, not a Supabase anon/service-role API key. URL-encode special password characters.
For verify-full, download the Supabase CA certificate from Database → Settings → SSL Configuration (https://supabase.com/dashboard/project/_/database/settings).
In Render's Environment page, add a Secret File named supabase-ca.crt. Paste the full downloaded PEM certificate, including BEGIN/END CERTIFICATE lines; it is CA material, not the database password. Docker services expose it at /etc/secrets/supabase-ca.crt.
Append this query to the database URL:
    ?sslmode=verify-full&sslrootcert=/etc/secrets/supabase-ca.crt
Use & rather than ? if the copied URL already has query parameters; replace any old sslrootcert value instead of adding it twice.
The system CA bundle alone may not trust the Supabase database CA. Do not change sslmode to require/disable or bypass certificate checks to make startup pass.
For the local transfer tool, use the path to the downloaded certificate on the machine running the transfer; /etc/secrets applies only to Render.

Official source: https://supabase.com/docs/guides/platform/ssl-enforcement

## 2. Preserve existing Render data BEFORE switching DATABASE_URL
Do not assume an empty Supabase database contains existing accounts, saved restaurants or campaigns.
Run this from a trusted machine with the repository dependencies installed:
    PYTHONPATH=backend .venv/bin/python -m app.transfer_postgres
The tool asks for the Render EXTERNAL database URL and Supabase SESSION pooler URL using hidden prompts. It prints counts only. No passwords, hashes or search histories are displayed.
It requires an empty application schema in the destination and never truncates or updates existing destination records. The source is read-only. Absent tables from older releases are skipped. All app tables are copied in FK order in one destination transaction, IDs are retained, sequences are advanced, and row hashes/counts are checked. Newer source columns unknown to the tool cause a refusal rather than silently dropping information.

For the final copy, pause all Render app writes and collection processes so no new data arrives after the snapshot. Then:
    PYTHONPATH=backend .venv/bin/python -m app.transfer_postgres --copy

A source snapshot alone cannot capture writes made after copying. Keep the old database intact until cutover checks pass. For a large database use a reviewed native PostgreSQL backup/restore instead of this small-app transfer helper.
If you explicitly choose a fresh start, skip copying with the understanding that Render accounts/data will not appear in Supabase.

## 3. Change the existing Render web service
Render → biteai-demo → Environment:
- DATABASE_URL: the Supabase session-pooler connection string, with TLS verification.
- AUTO_CREATE_SCHEMA=false (schema should already have been migrated).
- SEED_SAMPLE_DATA=false (do not populate the new database with fictional records).
- Keep the SAME JWT_SECRET so existing sessions can still refer to the preserved users.
- Keep CATALOG_WORKER_ENABLED=false during transfer. Restore true after verification if desired; sleeping Render services still pause collection.

Save and redeploy. Enter the URL only in Render's secure Environment settings, never chat, source files, screenshots or GitHub.
The blueprint now declares DATABASE_URL as a manual secret rather than automatically binding Render PostgreSQL. Existing deployments still require you to edit the value explicitly.

## 4. Verify before retiring anything
- https://biteai-demo.onrender.com/api/health reports database connected.
- Sign in with an existing account and check favourites/history/campaigns.
- Check matching source/target row counts from the transfer report.
- Confirm new writes appear in Supabase.
- Test search and owner permissions.
Vercel API_INTERNAL_URL remains https://biteai-demo.onrender.com/api. Do not replace it with a Supabase URL.

The legacy Render database remains in render.yaml deliberately to avoid accidentally deleting existing data during blueprint sync. Do not apply that legacy block to create an unnecessary database for a brand-new install. Once backup, transfer and cutover have been verified, retirement can be a separate explicit action. This update does not delete Render resources or move data automatically.
