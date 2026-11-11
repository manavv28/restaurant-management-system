# Keep Render Free; move the database to Supabase Free

Target: Vercel frontend → existing Render FastAPI/Next.js service → Supabase PostgreSQL.
No Google Cloud project or billing is needed. Cloud Run scripts remain optional alternatives and are not run.
Render still sleeps on its free plan. Supabase has its own free-plan quotas/inactivity rules; this does not make background collection always-on.

## 1. Prepare Supabase
In your existing Supabase project open SQL Editor. On a fresh application schema, run these files in order:
- supabase/migrations/001_initial.sql
- supabase/migrations/002_catalog_agents.sql
- supabase/migrations/20261111071209_sessions_and_privilege_hardening.sql

These create application tables, indexes and RLS restrictions. If BiteAI tables already exist, do not drop them to make migration pass. Inspect the existing schema first.
Open Connect → Session pooler and copy the PostgreSQL connection string on port 5432. Use the database password, not a Supabase anon/service-role API key. URL-encode special password characters. The updated Docker image downloads and bundles Supabase's official public CA over verified HTTPS during its build, alongside the system trust roots. It validates the certificate before shipping the image.
No dashboard Secret File upload is needed. Use:
    ?sslmode=verify-full
If you already configured sslrootcert=/etc/secrets/supabase-ca.crt and that file is missing, the application automatically uses the image's bundle instead. The earlier system-bundle path also maps to the combined trust bundle. Existing explicitly uploaded certificates are honoured.
Certificate and hostname verification remain enabled. This does not replace the password or change the database hostname.
For local tooling or an explicitly configured custom CA file, use the downloaded certificate's real local path. Do not disable certificate checks to work around missing files.

Official certificate source and provenance: backend/app/certs/README.md
Official guidance: https://supabase.com/docs/guides/platform/ssl-enforcement

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
- Keep the SAME JWT_SECRET. Accounts/passwords remain intact; pre-session-table JWTs require one fresh sign-in after this upgrade.
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


## Integration recovery, 11 November 2026

The confirmed baseline is `3be2c86` on `deploy/biteai-mvp`. Remote `main` remains older at `77b0410`. The attached workspace had no old checkout, reflog, stash or loose objects to recover; later unpushed edits were not recovered.

The existing `restaurant-management` Supabase project already contained the 001/002 application tables. Only the additive session migration above was applied during this recovery; its Supabase migration version is `20261111071209`. Do not replay 001/002 or run an unreviewed `supabase db push` against this manually initialized project. Its earlier SQL-editor setup is not recorded in CLI history. The optional `app.cloud_run migrate` runner also uses a separate checksum ledger and is for fresh databases or databases already managed by that runner; do not use it to adopt this existing project implicitly.

For a **new install**, use `render-supabase.yaml`, which provisions only the Render Free Docker web service. `render.yaml` retains the legacy database declaration to avoid accidental retirement during an existing Blueprint sync. Existing services should receive reviewed environment edits directly. Neither file provisions Google Cloud resources. The root image includes SQL migration files; fresh-database migrations can be run from a trusted checkout with `PYTHONPATH=backend MIGRATIONS_DIR=supabase/migrations python -m app.cloud_run migrate` before starting the app. Free Render services do not use a paid pre-deploy job.

The target defaults are `AUTO_CREATE_SCHEMA=false`, `SEED_SAMPLE_DATA=false`, `ENABLE_PAYMENT_SIMULATION=false`, and `CATALOG_WORKER_ENABLED=false`. Enable collection explicitly after approving sources; it pauses while the free service sleeps. Run retention (`python -m app.jobs`) from an operator-controlled scheduler; this change does not claim always-on scheduling.

Browser auth must use the same-origin `/api` rewrite. Cookies are HttpOnly, SameSite=Lax and Secure in production, backed by expiring database sessions. Browser mutations send `X-BiteAI-Client: browser`; this header is deliberately excluded from cross-origin CORS access. Bearer API clients remain supported. Deploy the frontend and backend from the same revision together. Update `API_INTERNAL_URL` only as described above; Next.js embeds rewrite destinations at build time.

Current validation and remaining release gates are in [RECOVERY_VALIDATION.md](RECOVERY_VALIDATION.md). The new application revision has not been deployed to Render or Vercel.


## Verified migration-history adoption

During requirements completion, the hosted schema was compared with an isolated migrated database: column types/nullability, primary/foreign/check/unique constraints, indexes and RLS/browser-role access matched (excluding the additional optional PostGIS index). The seven SQL files are now recorded with SHA-256 checksums in `public.biteai_migrations`. Subsequent releases may use `PYTHONPATH=backend MIGRATIONS_DIR=supabase/migrations python -m app.cloud_run migrate`; the runner will skip verified old migrations and refuse edited checksums. Supabase CLI history still records the individual hosted changes, not the earlier manual baseline: do not use an unreviewed `supabase db push`.

For another manually initialized database, `python -m app.adopt_migrations` first audits the current full schema without changing it; only an explicit `--adopt` records checksums after the audit passes. Take a backup first. Do not use adoption to conceal schema drift or skip unapplied migrations.

Retention is supervised in-process by default and runs every six hours while awake. Free service sleeping pauses both collection and retention; startup/wake resumes the worker. No paid scheduler is created.
