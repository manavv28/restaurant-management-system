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
- [x] Honest handling of unknown menus/prices. None were inferred from OSM. Current pilot coverage is 91 source-observed dishes for one restaurant; other listings may remain unpriced. See [MENU_PILOT.md](MENU_PILOT.md).
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
- [x] Backend PostgreSQL suite: **58 passed**. SQLite: **53 passed, 5 PostgreSQL-only skips**; ten browser journeys cover core flows, cookie revocation, location permission/denial, voice adapter/fallback and checkout-status behavior.
- [x] Production frontend build/TypeScript checks passed.
- [x] CI runs PostgreSQL/schema/transfer tests, browser journeys, the actual production Docker build and image smoke checks on a hosted builder.

## Hosting verification completed

- [x] Hosted CI image build and non-root database-backed image smoke check passed: Actions run 42988831331.
- [x] PRs #4 and #3 merged into deploy/biteai-mvp; matching release deployed to Render and the selected Vercel production project.
- [x] Both public API origins verified: matching release, Supabase verify-full TLS, real catalog/freshness, Secure/HttpOnly/SameSite cookies, CSRF, consent persistence, owner isolation, login and logout/replay rejection.
- [x] Hosted live-browser check passed against the public mobile UI with normal certificate validation: [run 42988831196](https://github.com/manavv28/restaurant-management-system/actions/runs/42988831196). Its artifact includes the mobile screenshot. Local external-browser CA/profile limitations were handled by using the hosted runner; certificate verification was never disabled.

## Requires external configuration or evidence

See [REQUIRED_CONFIGURATION.md](REQUIRED_CONFIGURATION.md) for the exact inputs, secure environment-variable placement, and follow-up validation.

- [ ] Approve restaurant website domains, collect real menus/prices, and verify the complete real dish/budget-match journey. The 10-listing Bandra pilot added 91 source-observed Hakkasan dishes and verified a real budget match. Broader coverage remains incomplete; automatic Render refresh is blocked by publisher HTTP 403. Prices cannot be fabricated or collected from unapproved hosts.
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

## Final release and reliability verification

Application release `9c8cece4268db8d82341dd774446b4df5412543b` is deployed on both selected origins. Live testing exposed synchronous catalog scans blocking the API event loop and causing Render health timeouts. The fix moves database search work to the thread pool, releases read transactions before provider calls, uses a correlated anti-join and indexed geographic prefilter for unknown-price results, and binds/verifies the public frontend before starting background workers. Regression tests prove health remains responsive while database search waits and unknown-price listing performs at most two SELECTs for 80 restaurants.

[Final integration run 42988831331](https://github.com/manavv28/restaurant-management-system/actions/runs/42988831331) passed all 58 PostgreSQL checks, 10 Chromium journeys, frontend build/typecheck, production Docker build and non-root image/database smoke test. [Live browser run 42988831196](https://github.com/manavv28/restaurant-management-system/actions/runs/42988831196) passed the real production catalog/modal/attribution/mobile-layout checks with TLS validation enabled. Both public API origins also passed secure-cookie, CSRF, consent, owner isolation, login, private-history and logout/replay checks after the fix. No subsequent Render restart/failure event was observed during verification. Test fixture accounts were removed.

Real microphone transcription still needs confirmation in a supported end-user browser; automated voice-recognition and unsupported-browser tests use a controlled adapter fixture. The backend remains on Render Free, with Supabase verify-full TLS and no paid infrastructure added.

## Backup and email setup follow-up

Daily encrypted backup and health-check automation is implemented in `.github/workflows/operations.yml`; Gmail sender/alert recipient is letsbiteai@gmail.com. Seven-day artifact retention is configured. Encryption round-trip, wrong-key rejection, failed-dump cleanup and incomplete-SMTP readiness have automated coverage. See [BACKUPS.md](BACKUPS.md) for secure secrets, restore steps and the default-branch scheduling prerequisite. Production backup creation/recovery and actual mail/alert delivery remain unchecked until credentials and activation are complete.

## Release verification, 11 November 2026 follow-up

Release `4348aa17505414c558c6be7633aed0cad963a5b4` is live on the selected Vercel project and Render Free service. [Integration run 43045717971](https://github.com/manavv28/restaurant-management-system/actions/runs/43045717971) passed 62 PostgreSQL tests, ten browser journeys, migrations/idempotence, frontend build, production Docker build and non-root database-backed image smoke verification. [Public browser run 43045879647](https://github.com/manavv28/restaurant-management-system/actions/runs/43045879647) passed. Both public APIs report the matching release, Supabase verify-full TLS, 378 real restaurants, zero sample restaurants and zero source-backed menu prices; search returns honestly unpriced nearby discoveries. CI runners are pinned to Ubuntu 24.04 and use preinstalled Chrome, avoiding the Ubuntu package-server DNS failure encountered while installing browser dependencies.

The user selected Google as the restaurant discovery route and has no restaurant-authorized menu sources to supply. The existing Google Places adapter requires a securely configured Places API key; this choice does not establish real dish/price coverage. Gmail App Password creation was explained; no App Password or backup credential has been provided. Repository secret-settings access returns HTTP 403 for the connected GitHub integration. No secret values were requested in chat. [Draft PR #5](https://github.com/manavv28/restaurant-management-system/pull/5) prepares the default-branch schedule, pending secure configuration and activation. Email/alerts, encrypted production backup/recovery, external AI/Maps calls, merchant sandbox certification and real microphone transcription remain unverified.

## Email delivery incident, 12 November 2026

The verification button did submit requests, but Render Free blocks Gmail SMTP port 465. Production logs show delivery failures (503), followed by duplicate-click throttling (429). Email availability previously established configuration presence only, not delivery. The prepared fix uses the existing Vercel production project as a server-only, HMAC-authenticated HTTPS security-mail relay, while retaining Render Free and Supabase. The verification panel now shows pending state, prevents duplicate requests and displays delivery/session/rate-limit errors. See [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md) for credential flow, tests and activation prerequisites. Explicit authorization is required after automatic approval review rejected storing the new production signing secret in Vercel. Neither relay activation nor successful production delivery is claimed yet.

## Email relay activation verified, 12 November 2026

User approved activation explicitly; PR #6 merged. Production release `381d7c93dffc` is live on the selected Vercel project and Render Free backend. The server-only signing key is stored in both production services, and Render uses authenticated HTTPS for mail delivery. A real operator test returned HTTP 200 after Gmail accepted the message for letsbiteai@gmail.com. Unsigned relay access returned HTTP 401. Hosted integration run 43184829303 and live-browser run 43184829421 both passed. Supabase and Render Free are retained. Email configuration is enabled; inbox placement and the user's actual verification/reset link completion remain unconfirmed. See [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md) for the active credential flow.

## Priced-menu pilot verified, 12 November 2026

PRs #7 and #8 are merged. Release `a47fa39aae36` is live on both selected services, with Render Free and Supabase retained. Ten Bandra-area listings were investigated; one provided 91 explicit INR prices. The other nine remain unpriced due to missing prices, unavailable sources or branch mismatches. PDF/image inspection produces review candidates only.

Direct Render collection of the approved Hakkasan URL hit HTTP 403 (job 31). A separately fetched public publisher snapshot was imported with its actual hash, source time and 48-hour expiry (job 32, audit 1). This is not reported as a successful automatic refresh. Both live APIs matched Spicy jackfruit dumpling at ₹595 under a ₹1000 budget and returned all 91 source-backed menu items. The snapshot expires on 14 November 2026 at 14:46 IST unless refreshed.

Local PostgreSQL: 73 passed. Hosted follow-up: 72 passed, one native-PDF-only skip; 14 browser journeys, frontend/Docker builds and image smoke passed. Final release integration run 43191707994 and live-browser run 43191707700 passed. The new price-data query regression prevents per-dish read growth. [MENU_PILOT.md](MENU_PILOT.md) records sources, evidence and remaining limits. Google Places keys, broader menu coverage, automatic source refresh and the other external-configuration checkpoints remain outstanding.
