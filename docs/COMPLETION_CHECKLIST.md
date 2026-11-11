# BiteAI requirements completion

Updated 11 November 2026. Render Free + Supabase PostgreSQL remain the hosting target. The selected frontend is restaurant-management-system-qxtx.vercel.app.

## Implemented and verified

- [x] Recover confirmed baseline and preserve work in Git.
- [x] Revocable HttpOnly browser sessions; private account endpoints; customer/owner boundaries.
- [x] Persistent database-backed authentication throttling.
- [x] One-use, expiring, hashed email verification/password-reset tokens; password reset revokes all sessions. SMTP delivery is implemented and tested with a mail fixture.
- [x] DNS TXT proof of restaurant website control; changing the website invalidates verification. This proves domain control, not legal merchant identity.
- [x] Approved menu-link discovery, structured menu extraction, evidence-checked Gemini adapter, category classification, price-change audits and source controls.
- [x] Live OSM collection: **378 distinct real records across Bandra, Andheri, Powai, Colaba and Dadar**, imported with source attribution and actual collection-job traces into Supabase. Two transient provider failures succeeded on the bounded retry run.
- [x] Honest handling of unknown menus/prices. None were inferred from OSM. Current source-backed menu-price coverage remains zero.
- [x] Price/distance/rating ranking and saved-cuisine recommendations.
- [x] Missing-match follow-up and optional Google Places fallback that labels discoveries as unpriced and does not persist provider content indefinitely.
- [x] Popular-dish and recommendation panels; cards support source/freshness, photos/attribution, ratings/review counts, contacts, directions, external menu/ordering links and eligible offers.
- [x] Restaurant details/menu management includes PIN code, menu category and description.
- [x] Google Maps component with Advanced Markers, optional restricted browser key, and working Leaflet fallback.
- [x] Cuisine/dish/area analytics and attributed search-to-click conversion. Signed attribution is scoped to returned results and the requesting account; replayed clicks are deduplicated. Owners receive aggregates only.
- [x] Campaign reservation/discount/order-value reporting; reservations are never reported as sales.
- [x] Signed refund/dispute events adjust eligibility; refund replay and delayed dispute events are tested. Browser callbacks cannot credit spending.
- [x] PostGIS enabled in the unexposed extensions schema, geography GiST index, and indexed proximity prefilter with deterministic final distance checks. Portable SQL bounding-box fallback remains available.
- [x] Additive migrations applied to live Supabase. Hosted columns, constraints, indexes and browser-role access matched the isolated tested schema. Seven SQL checksums were recorded after verification; future releases use the checksum runner. Do not blindly replay baseline SQL or use CLI db push against this manually initialized project.
- [x] Retention worker runs every six hours while Render is awake; structured request IDs and sanitized server-error logs support diagnosis. No always-on worker is promised.
- [x] Isolated pg_dump/pg_restore rehearsal: 378 records, matching complete-row hash.
- [x] Legacy Render database inspected read-only: zero users/favourites/transactions; six sample restaurants and sample campaigns. Nothing was deleted or automatically transferred.
- [x] Backend PostgreSQL suite: **56 passed**. SQLite suite and browser results are in the current work report; ten browser journeys cover core flows, cookie revocation, location permission/denial, voice adapter/fallback and checkout-status behavior.
- [x] Production frontend build/TypeScript checks passed.
- [x] CI runs PostgreSQL/schema/transfer tests, browser journeys, the actual production Docker build and image smoke checks on a hosted builder.

## Hosting verification in progress

- [x] Hosted CI image build and non-root database-backed image smoke check passed: Actions run 42984898701.
- [x] PRs #4 and #3 merged into deploy/biteai-mvp; matching release deployed to Render and the selected Vercel production project.
- [x] Both public API origins verified: matching release, Supabase verify-full TLS, real catalog/freshness, Secure/HttpOnly/SameSite cookies, CSRF, consent persistence, owner isolation, login and logout/replay rejection.
- [ ] Hosted live-browser check is running to verify the public mobile UI with normal certificate validation. Local external-browser automation hit environment CA/profile restrictions; TLS verification was never disabled.

## Requires external configuration or evidence

- [ ] Approve restaurant website domains for real menu collection. Broad discovery metadata is now present, but menus/prices cannot be fabricated or collected from unapproved hosts.
- [ ] Configure Gemini and Google Places keys and validate real provider responses/quotas. Optional Google Maps rendering requires a referrer-restricted browser key. Deterministic text search and Leaflet work without these keys.
- [ ] Configure TLS SMTP, sender identity and PUBLIC_APP_URL; verify actual email delivery and a real verification/reset email. No email was sent to a real user during tests.
- [ ] Complete legal merchant onboarding/settlement/routing and validate Razorpay sandbox captures/refunds/disputes end to end before enabling charges. Signed fixtures validate application behavior; they are not provider certification.
- [ ] Select/configure an alert destination and confirm a real incident notification. Request logs, health checks and CI failure status are available, but no external alert recipient was invented.
- [ ] Confirm production backup availability/retention and rehearse recovery using a protected production backup. The completed restore rehearsal uses isolated public catalog data.

The original MVP explicitly permits simulated payments and provider fallbacks. Those fallbacks do not establish real menu coverage, working email delivery, legal merchant approval or full production readiness.

## Published verification checkpoint

The implementation release `89f10fee1d96020e81b6c825969a314b0acfa403` was verified at both https://biteai-demo.onrender.com and https://restaurant-management-system-qxtx.vercel.app. Render's Free plan was confirmed after deployment. The actual deployed image includes retention and catalog workers; the catalog blueprint now preserves the enabled collection setting on future syncs. Live fixture accounts were removed after verification.

GitHub Actions run https://github.com/manavv28/restaurant-management-system/actions/runs/42984898701 passed 56 PostgreSQL tests, all 10 browser journeys, production frontend build, actual Docker build and non-root image/database smoke test. SQLite passed 51 tests with 5 PostgreSQL-only skips. The separate public-release workflow captures a mobile screenshot and checks the current production origin without weakening browser certificate checks.

The remaining unchecked external-configuration items above still prevent a full production-ready claim. The application runs with explicit provider fallbacks and unknown menu prices.
