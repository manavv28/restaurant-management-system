# BiteAI requirements completion

Updated 13 November 2026 (India). Render Free + Supabase PostgreSQL remain the hosting target. The selected frontend is restaurant-management-system-qxtx.vercel.app.

## Implemented and verified

- [x] Recover confirmed baseline and preserve work in Git.
- [x] Revocable HttpOnly browser sessions; private account endpoints; customer/owner boundaries.
- [x] Persistent database-backed authentication throttling.
- [x] One-use, expiring, hashed email verification/password-reset tokens; password reset revokes all sessions. SMTP delivery is implemented and tested with a mail fixture.
- [x] DNS TXT proof of restaurant website control; changing the website invalidates verification. This proves domain control, not legal merchant identity.
- [x] Approved menu-link discovery, structured menu extraction, evidence-checked Gemini adapter, category classification, price-change audits and source controls.
- [x] Citywide public-source catalog: **10,404 source-backed listings across 48 Mumbai search areas**, including 10,026 added Overture records and the existing 378 OSM records. Provenance aliases, licences, district clipping, conservative duplicate matching and unknown-price labels are retained. This is not an exhaustive or independently verified census. See [CITYWIDE_CATALOG.md](CITYWIDE_CATALOG.md).
- [x] Honest handling of unknown menus/prices. None were inferred from OSM. **357,694 listed dish prices across 2,613 restaurants** are published. Public menu API coverage is documented in [PUBLIC_MENU_PRICES.md](PUBLIC_MENU_PRICES.md); third-party prices retain original dates and ordering context. Existing publisher and owner menus are protected. Coverage remains incomplete; unknown prices are never invented.
- [x] Price/distance/rating ranking and saved-cuisine recommendations.
- [x] Missing-match follow-up and optional Google Places fallback that labels discoveries as unpriced and does not persist provider content indefinitely.
- [x] Popular-dish and recommendation panels; cards support source/freshness, photos/attribution, ratings/review counts, contacts, directions, external menu/ordering links and eligible offers.
- [x] Restaurant details/menu management includes PIN code, menu category and description.
- [x] Google Maps component with Advanced Markers, optional restricted browser key, and working Leaflet fallback.
- [x] Cuisine/dish/area analytics and attributed search-to-click conversion. Signed attribution is scoped to returned results and the requesting account; replayed clicks are deduplicated. Owners receive aggregates only.
- [x] Campaign reservation/discount/order-value reporting; reservations are never reported as sales.
- [x] Signed refund/dispute events adjust eligibility; refund replay and delayed dispute events are tested. Browser callbacks cannot credit spending.
- [x] PostGIS enabled in the unexposed extensions schema, geography GiST index, and indexed proximity prefilter with deterministic final distance checks. Portable SQL bounding-box fallback remains available.
- [x] Additive migrations applied to live Supabase. Hosted columns, constraints, indexes and browser-role access matched the isolated tested schema. Ten SQL checksums were recorded after verification; future releases use the checksum runner. Do not blindly replay baseline SQL or use CLI db push against this manually initialized project.
- [x] Retention worker runs every six hours while Render is awake; structured request IDs and sanitized server-error logs support diagnosis. No always-on worker is promised.
- [x] Isolated pg_dump/pg_restore rehearsal: 378 records, matching complete-row hash.
- [x] Legacy Render database inspected read-only: zero users/favourites/transactions; six sample restaurants and sample campaigns. Nothing was deleted or automatically transferred.
- [x] Backend PostgreSQL suite: **87 passed locally; 86 passed and one native-PDF-only skip in hosted CI**. All **24 browser checks** pass, including source dates, fractional rupees, menu links, startup recovery and core account flows.
- [x] Production frontend build/TypeScript checks passed.
- [x] CI runs PostgreSQL/schema/transfer tests, browser journeys, the actual production Docker build and image smoke checks on a hosted builder.

## Hosting verification completed

- [x] Hosted CI image build and non-root database-backed image smoke check passed: Actions run 42988831331.
- [x] PRs #4 and #3 merged into deploy/biteai-mvp; matching release deployed to Render and the selected Vercel production project.
- [x] Both public API origins verified: matching release, Supabase verify-full TLS, real catalog/freshness, Secure/HttpOnly/SameSite cookies, CSRF, consent persistence, owner isolation, login and logout/replay rejection.
- [x] Hosted live-browser check passed against the public mobile UI with normal certificate validation: [run 42988831196](https://github.com/manavv28/restaurant-management-system/actions/runs/42988831196). Its artifact includes the mobile screenshot. Local external-browser CA/profile limitations were handled by using the hosted runner; certificate verification was never disabled.

## Requires external configuration or evidence

See [REQUIRED_CONFIGURATION.md](REQUIRED_CONFIGURATION.md) for the exact inputs, secure environment-variable placement, and follow-up validation.

- [ ] Expand coverage where usable menus remain unavailable and confirm current restaurant prices. The public API import and actual Render refresh are verified; the original Hakkasan publisher still returns HTTP 403 to Render. Published third-party prices are reference observations, not live restaurant quotes.
- [ ] Configure Gemini and Google Places keys and validate real provider responses/quotas. Optional Google Maps rendering requires a referrer-restricted browser key. Deterministic text search and Leaflet work without these keys.
- [ ] Confirm inbox placement and completion of the real verification/reset link. The configured HTTPS security-mail relay delivered a Gmail-accepted message for letsbiteai@gmail.com; see [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md).
- [ ] Complete legal merchant onboarding/settlement/routing and validate Razorpay sandbox captures/refunds/disputes end to end before enabling charges. Signed fixtures validate application behavior; they are not provider certification.
- [ ] Confirm a real incident notification to the selected letsbiteai@gmail.com address. Request logs, health checks and CI failure status are available.
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

## Startup/search screenshot incident resolved, 12 November 2026

Release `25cd602bb39e` is live on the selected origins. JSON validation, bounded read-only readiness checks, visible startup feedback and search-generation guards address HTML/proxy responses during startup. Coverage refreshes after search and on focus/visibility instead of retaining a mount-time zero. Search POSTs are not automatically replayed. Stable marker inputs preserve map popups during late startup state changes. All 17 browser tests passed; final integration run 43205988098 and live-browser run 43205988068 passed. Both APIs still report 91 fresh observations and return the exact ₹595 dumpling query. No database data, credentials, migrations or hosting plans changed. See [STARTUP_RECOVERY.md](STARTUP_RECOVERY.md).


## Citywide catalog release, 12 November 2026

Release `5a8a345196e4362b4a6d6fa644a0890e6a8e197d` is live on Render Free and the selected Vercel project. Supabase contains 10,404 real-source listings, no fictional samples, 10,155 Overture provenance aliases, and all 91 preserved Hakkasan menu items. No menu prices, opening hours or ratings were inferred. Coverage spans Mumbai City and Mumbai Suburban district polygons; Thane and Navi Mumbai are excluded. Provider errors, stale businesses and spelling duplicates may remain.

The additive identity migration was tested, applied and verified with RLS and browser access revoked. All 79 local PostgreSQL checks passed; hosted CI passed 78 checks with one native PDF test skipped, 19 browser journeys, production build, Docker build and non-root database-backed image smoke checks, including licence-file delivery. [Final integration](https://github.com/manavv28/restaurant-management-system/actions/runs/43244710642) and [public browser verification](https://github.com/manavv28/restaurant-management-system/actions/runs/43244710830) passed. Both public APIs report the matching release, 48 search areas, 10,404 listings and Supabase verify-full TLS. The real directory was additionally checked for Borivali filtering, pagination, source modal and mobile overflow. In the managed executor, public resources were fetched through Playwright's TLS-validating Node client using the supplied proxy/CA bundle; certificate checks were not disabled. Hosted public browser verification uses normal browser TLS.

[Production import evidence](catalog/mumbai-2026-11-12-production.json) records batches, deployment IDs, migration checksum and counts. The restaurant directory supports name/area filters and bounded pages. Source licences and full Foursquare notice are available on `/data-sources` and `/notices/*` on both origins. The existing menu, payments, backup and other external-configuration limitations remain; this catalog expansion does not establish full production readiness.

The final integration audit separated the 48 search areas from the original five OSM collection areas. It disabled 43 unintentionally auto-seeded, never-successful sources and cancelled their pending jobs; no listings or menus were removed. No jobs remain active for disabled sources. Regression checks cover bounded seeding, explicit additional-area selection and terminal disabled jobs. Directory visits also omit unrelated food-search attribution; the public click endpoint returned 200 during the final browser check. The final Render error-log scan was empty.

## Search connection recovery follow-up, 12 November 2026

Release `086e67bbd4718aa377fd0e7d527821aa630b8031` is live on both selected origins. A failed readiness check now shows an inline retry state rather than false zero matches; a healthy catalog can establish readiness if the health probe fails. Health responses are dynamic, bounded and explicitly non-cacheable, and account refresh no longer holds the search spinner after results arrive. Full CI and public browser verification passed, including forced readiness timeout, fallback and single-POST retry checks. See [STARTUP_RECOVERY.md](STARTUP_RECOVERY.md) for evidence and limits. The original intermittent end-user transport failure was not reproduced, and no specific cause is claimed as confirmed.

## Public menu price release, 13 November 2026 (India)

Release `abae206e042a` is deployed on the selected Vercel frontend and Render Free backend. Supabase migration nine is applied with its checksum; RLS remains enabled. [Hosted integration](https://github.com/manavv28/restaurant-management-system/actions/runs/43286798643) and [public browser verification](https://github.com/manavv28/restaurant-management-system/actions/runs/43286798536) passed. A real supervised API refresh succeeded (job 76, source 484) on its first attempt. Bounded SQL ranking, idempotent batches, source attribution and original publisher preservation were tested against more than 300,000 prices. The final collection and publication totals are recorded in [the price report](catalog/menu-prices-2026-11-13.json).

## Official platforms and contacts, 13 November 2026 (India)

Release `3678a24e8044` adds official provider account links, protected credential tables, read-only Swiggy tools and Zomato authenticated-contract capture. Actual provider login and live reads still require user account consent. Both provider registrations accepted callback requests; this is not a claim of working authenticated price comparison. Hosted CI passed 99 backend tests plus one PDF skip and all 28 browser checks. Forty-seven public contacts were published with per-number evidence; 8,747 listings now have phone numbers. See [USER_BRIEF_CHECKLIST.md](USER_BRIEF_CHECKLIST.md) for the checklist against the exact original MVP brief and [the rollout evidence](catalog/provider-contacts-2026-11-13.json).

## Presentation release, 13 November 2026 (India)

Release `082b9205c959` is live on Vercel and Render Free. Consistent controls, provider status badges, accessible accordions and improved mobile presentation are complete. Hosted validation passed 99 backend tests plus one PDF skip and 29 browser journeys; both public release checks passed. See [IMPLEMENTATION_VERIFICATION.md](IMPLEMENTATION_VERIFICATION.md) for release evidence and the exact remaining original-brief dependencies. No blanket production-readiness claim is made.
