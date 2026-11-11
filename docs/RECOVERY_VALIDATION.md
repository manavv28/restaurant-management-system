# BiteAI recovery and integration validation

Historical recovery checkpoint. See [COMPLETION_CHECKLIST.md](COMPLETION_CHECKLIST.md) for subsequent work and current release gates.

Date: 11 November 2026 (Asia/Kolkata). **Not deployment-ready.**

## Recovery evidence

- The attached `/workspace` contained no application files; its `.git` directory was empty and not a repository. Shared downloads and library files were empty.
- Cloned `manavv28/restaurant-management-system`. Remote `main` is `77b0410`; `deploy/biteai-mvp` is the confirmed `3be2c869c00db3d6b9aa91a8766ecb8798680ff1`.
- Available branch and pull-request refs contain no newer work. No old workspace objects, stash or reflog were available. The unfinished edits were not recovered; this branch implements new changes from the confirmed baseline.

## Changes

- Browser auth uses HttpOnly, production-Secure, SameSite=Lax cookies and hashed, expiring, revocable database sessions. Logout revokes server-side access. Browser writes require a custom header; cross-origin CORS does not allow that header. Existing accounts/passwords remain; legacy JWTs require a fresh login.
- Source owners can pause collection, immediately withdraw source-backed prices, and queue a deduplicated refresh. Re-enabling does not revive withdrawn evidence. Workers recheck the source under a row lock before persisting fetched data.
- Hosted checkout is connected to configured/onboarded real restaurants. Browser callbacks cannot credit spending. Order status is account-scoped. Signed webhook validation rejects malformed identifiers and conflicting payment references; consent updates and capture processing lock the user row.
- Render Free remains the backend host, Supabase remains the database. Fresh installs use `render-supabase.yaml` without a Render database. Sample seeding, simulation, schema autocreation and catalog collection default off in deployment configuration. The legacy root Blueprint database declaration remains for existing-resource preservation.
- Production startup checks every model table/column. The image includes migration files. The data-transfer helper now uses the same Supabase TLS/certificate normalization as the application.

## Completed validation

- SQLite backend: **43 passed, 5 skipped**. The skipped tests require isolated PostgreSQL migration/transfer fixtures and passed in the PostgreSQL run.
- PostgreSQL 17 backend, migrations and transfer tests: **48 passed**. Includes schema/model column parity, RLS/access denial for browser roles, transfer hashes/IDs/sequences, and nonempty/unknown-schema refusal. One third-party Starlette/AnyIO deprecation warning remains.
- Fresh 001 → 002 → session migration chain succeeded; a second checksum-runner invocation made no changes. Migration timestamp was aligned with the Supabase-assigned version after application; local fixture ledger names were aligned as well.
- Playwright/Chromium against Next.js and a migrated PostgreSQL backend: **6 passed**. Covers search/menu/favourites/consent, mobile/map, owner listing/menu/campaign, rejected unapproved sources, cookie persistence and revoked-token replay, and checkout callback versus verified status. Checkout is mocked; no money moved.
- Next.js production build and its TypeScript validation passed.
- Built standalone frontend and FastAPI ran through the production supervisor against isolated PostgreSQL. HTML, proxied database health, Secure/HttpOnly cookie forwarding, authenticated requests, logout/replay rejection and disabled simulation passed.
- Official Supabase CA downloaded over verified HTTPS and validated. Downloaded CA SHA-256: `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`.
- Existing Render `/api/health` returned HTTP 200 and database connected. This describes the existing release, not the new code or proof of its database destination.

## Live Supabase change

Project `restaurant-management` (`dtzjhhqjuaucrfwtrepv`) already had the 16 baseline application tables with RLS. Applied only `20261111071209_sessions_and_privilege_hardening.sql`; no existing application data was reset or transferred.

Verified the new session table has RLS and neither `anon` nor `authenticated` can SELECT/INSERT/UPDATE/DELETE it. Revoked unnecessary public execution of `public.rls_auto_enable()` while preserving its internal event-trigger behavior. Verified both browser roles lack execute permission afterward. The security advisor now reports only 17 informational [RLS enabled with no policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy) findings, expected for this backend-only schema.

The baseline SQL-editor setup had no migration history. The new migration is recorded in Supabase history; do not replay baseline DDL or implicitly adopt this database with the separate checksum migration runner. See [RENDER_SUPABASE.md](RENDER_SUPABASE.md).

## Remaining release gates

1. **Docker image build:** attempted the actual root Dockerfile with CA build secrets. Docker's VFS layer preparation exhausted this environment's 7.9 GiB filesystem (`ResourceExhausted: no space left on device`). Removed attempt build cache. A complete image build/run still needs a builder with sufficient disk; the successful standalone supervisor test does not replace it.
2. **Coordinated deployment:** new code is not deployed to Render/Vercel. Confirm existing Render environment, Supabase connection destination and deployed revision; deploy frontend/backend together, then repeat real-origin cookie/login/logout, search, owner/source and migration checks. Preserve the legacy database until its existing data/backup/cutover has been verified. Direct Render DB credentials were not available here, so no transfer or TLS connection through the deployed application's credentials was performed.
3. **External providers:** no Gemini/Places credentialed validation or Razorpay sandbox capture was performed. Merchant settlement/routing, refunds, disputes and reconciliation remain unverified. Keep live charging disabled pending those checks.
4. **Existing production gates:** email verification/password reset, restaurant ownership verification, durable/distributed auth throttling, monitoring, backup/restore rehearsal and a retention scheduler remain required. Free Render sleeps and pauses in-process collection; no always-on worker is promised.

No Render/Vercel deployment or paid infrastructure was created by this recovery.
