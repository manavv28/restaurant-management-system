# Current BiteAI status

Updated 13 November 2026 (India). Release `3678a24e8044` is live at https://restaurant-management-system-qxtx.vercel.app with https://biteai-demo.onrender.com as its backend. Render remains on Free; Supabase remains the database with verify-full TLS. No paid service was provisioned.

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
