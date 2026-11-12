# Current BiteAI status

Updated 13 November 2026 (India). Release `082b9205c959` is live at https://restaurant-management-system-qxtx.vercel.app with https://biteai-demo.onrender.com as its backend. Render remains on Free; Supabase remains the database with verify-full TLS. No paid service was provisioned.

The catalog contains **10,404 real-source Mumbai listings and no fictional samples**, with **357,694 source-listed dish prices across 2,613 restaurants**. **8,747 listings have contact numbers; 1,657 still do not.** Public API menu prices retain original source dates, delivery context, retrieval times and source links. They are labelled third-party listed prices, not current restaurant-confirmed quotes. The existing 91 Hakkasan publisher prices were preserved. See [the current price report](catalog/menu-prices-2026-11-13.json), [collection rules](PUBLIC_MENU_PRICES.md) and [citywide source notices](CITYWIDE_CATALOG.md). Some restaurants still lack usable priced menus; coverage is not exhaustive or independently verified.

The public API import is idempotent, protects publisher/owner menus and pauses at a 425 MiB database budget. A real Render worker refresh succeeded on its first attempt (job 76). The worker runs while Render Free is awake; freshness is not an always-on guarantee. The original Hakkasan publisher continues to block direct Render collection with HTTP 403.

Verification: the full local baseline passed, followed by targeted provider-security checks; hosted CI passed 99 with one native-PDF-only skip, all 28 browser checks, frontend build, production Docker build and non-root database smoke. [Release integration](https://github.com/manavv28/restaurant-management-system/actions/runs/43309011590) and [public browser verification](https://github.com/manavv28/restaurant-management-system/actions/runs/43309011561) passed. Additional public checks covered dated price attribution, mobile layout, directory pagination, source notices, bounded results and explicit search recovery. Large-data import/replay preserved the publisher menu. Ten migration checksums are recorded; private-table RLS remains enabled.

Email uses the configured, authenticated Vercel HTTPS relay because Render Free blocks Gmail SMTP. Gmail accepted the operator delivery test for letsbiteai@gmail.com. Actual inbox placement and completion of the user's verification/reset link remain unconfirmed. See [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md).

Remaining external prerequisites are listed in [COMPLETION_CHECKLIST.md](COMPLETION_CHECKLIST.md) and [REQUIRED_CONFIGURATION.md](REQUIRED_CONFIGURATION.md):

- Confirm real verification/reset link completion and incident notification delivery.
- Configure the selected encrypted GitHub-artifact backup workflow with secure credentials and rehearse protected production recovery.
- Complete merchant onboarding and real provider sandbox capture/refund/dispute validation before enabling charges. Real payments remain disabled.
- Optional Gemini/Google APIs require keys and provider validation; deterministic text search and Leaflet work without them.
- Expand missing menu coverage and confirm current prices with restaurants where possible.

These prerequisites prevent a blanket production-ready claim. Earlier recovery and deployment evidence remains in Git history and the linked checkpoint documents.

Official provider account connection controls are live. Swiggy has a read-only adapter; Zomato account linking captures its authenticated tool contract before live business mapping is enabled. Both provider client registrations accepted the callback requests, but no actual provider accounts were connected during verification. Connect accounts through the app to complete live reads; no consumer password or OTP belongs in chat. See [PLATFORM_CONNECTIONS.md](PLATFORM_CONNECTIONS.md), [PUBLIC_CONTACTS.md](PUBLIC_CONTACTS.md), [the release report](catalog/provider-contacts-2026-11-13.json), and [the checklist against the user brief](USER_BRIEF_CHECKLIST.md).

## Presentation and verification update

Release `082b9205c959` (PR #17) is live on both selected services. Search, connection, directory, account/portal and menu controls now have consistent states, clearer hierarchy and responsive spacing. Mobile restaurant cards use a single readable column. Keyboard connection tests also cover pending-request disabling and recoverable errors. No schema/data changes or paid resources were introduced.

[Release integration](https://github.com/manavv28/restaurant-management-system/actions/runs/43315503798) passed 99 backend tests (one native-PDF skip), 29 browser journeys, migration checks, production builds and Docker smoke. [Public release verification](https://github.com/manavv28/restaurant-management-system/actions/runs/43315503732) passed both public browser/API checks. The live original-brief Haka-noodles request returned 15 source-listed matches within ₹300/2 km in Bandra. Additional public browser checks verified contact-source links, correct telephone links, zero mobile overflow and zero page/request failures. The post-live Render error/traceback scan was empty.

Provider accounts remain unconnected; the live parser remains local rules and actual payments remain unavailable/disabled. Missing catalogue data, OAuth/model/payment configuration, mailbox/device checks and protected production recovery remain open in [IMPLEMENTATION_VERIFICATION.md](IMPLEMENTATION_VERIFICATION.md). UI release verification does not certify completion of the entire original brief.
