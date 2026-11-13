# Current BiteAI status

Updated 13 November 2026. Application release `b317cefc3bfa` is deployed to [the selected frontend](https://restaurant-management-system-qxtx.vercel.app), with [Render Free](https://biteai-demo.onrender.com) as backend and Supabase PostgreSQL using verify-full TLS. No paid infrastructure was added.

The public catalogue contains **10,404 real-source venues**, **357,694 source-listed prices across 2,613 restaurants**, and **8,747 public contact numbers**. There are no fictional samples in production. **7,791 venues still lack priced menus and 1,657 lack contacts**; an exhaustive Mumbai census has not been established. Original source dates and price context remain visible. These are reference observations, not current delivery or restaurant-confirmed quotes.

## PRD work delivered

- `/concierge`: dark-first, full-screen interactive map, voice controls, streamed agent trace, database-backed verdict with selectable top-three restaurant/dish/price/distance options and explicit parsed constraints, nearest/cheaper follow-ups and dated confidence chips. The map remains available while queries load; the normal list view remains at `/`.
- Hinglish/Devanagari text parsing, explicit vegetarian/Jain/halal constraints, supported opening-hour checks, item budget/radius filters, party-size and ordering-mode cautions. Unknown facts fail closed.
- Bounded missing-menu research over reviewed sources, durable job records, background execution and re-query after each successful refresh. Actual public API research jobs 78–83 succeeded; the first three recorded 230 explicit dietary labels and the vegetarian Hakka-noodles query then returned a declared-vegetarian match. After the responsiveness fix, all three new checks completed while status/health requests stayed HTTP 200; the catalogue now holds 368 explicit dietary labels. Research does not bypass source restrictions.
- `/agents`: actual job/run activity; private administrator QA and claim review. Restaurant claim requests and conservative offer suggestions require independent review/owner approval.
- Query/spend tiers, same-dish 24-hour deduplication, monthly credit cap, cuisine conditions, weekly limits and restaurant discount budgets. Test spending never counts as verified real spending.
- Sandbox-only gateway order/capture logic, authenticated QR vouchers, once-only owner redemption, cancellation/expiry and refund/dispute revocation. Real provider credentials and merchant onboarding remain absent, so actual checkout is unavailable.
- Installable web manifest, privacy-safe offline explanation, reduced-motion handling, light/dark controls, improved mobile presentation and accessible buttons.
- Twelve checksummed migrations, private-table RLS/revoked browser access, source retention and protected publication. Applied migrations were not rewritten.

## Verification and practical limits

Hosted integration **[43407550923](https://github.com/manavv28/restaurant-management-system/actions/runs/43407550923)** passed **216 backend tests** (one native-PDF skip), **35 browser journeys**, migration/transfer checks, production frontend/Docker builds and non-root database smoke. Public release **[43407550899](https://github.com/manavv28/restaurant-management-system/actions/runs/43407550899)** passed the live checks. See [PRD traceability](PRD_TRACEABILITY.md) and [search latency evidence](SEARCH_LATENCY.md).

Five sequential warm original-brief probes returned 15 matches within ₹300/2 km, with a median verdict of **1.9 seconds**, improved from 13.5 seconds before the coverage-path fix. The first-event median was 835 ms in that test network. This does **not** certify a representative p95, the 600 ms first-event target or 100 concurrent users. Render Free can sleep.

Platform Connect was cut from the enabled MVP after actual Swiggy whitelist and Zomato OTP failures, as allowed by the PRD's optional spike. The app offers contextual **Browse on Zomato/Swiggy** links; these do not read authenticated prices. Both MCP feature flags are off and no authenticated account reads are claimed. See [provider evidence](PLATFORM_CONNECTIONS.md).

The [126-second public-app demo](demo/biteai-prd-demo.mp4) records the map, Hinglish text query/verdict, nearest follow-up, real source/coverage/menu details and Agent Wall with zero JavaScript page errors. It explicitly excludes actual microphone transcription, merchant payment and external account login. Managed-browser network interception buffers fetched streams, so the video is not first-event latency evidence. Two search requests were deliberately aborted by replacement/navigation; they were not HTTP 500 responses.

## Still open

The exact remaining requirements and required inputs are in [the completion checklist](COMPLETION_CHECKLIST.md), [the original-brief checklist](USER_BRIEF_CHECKLIST.md) and [secure configuration instructions](REQUIRED_CONFIGURATION.md). They include missing catalogue data, actual phone speech verification, a live model key, participating merchant/gateway validation, mailbox/incident delivery, protected production recovery, and PRD performance/data-quality evidence. P1 receipt/Account Aggregator work and semantic embeddings remain open.

Gmail accepted the configured HTTPS relay's delivery test for **letsbiteai@gmail.com**; inbox receipt and actual verification/reset completion remain unconfirmed. Full application access does not supply missing provider credentials, merchant identity or unknown restaurant facts. The entire PRD is not certified complete or production-ready.

Machine-readable release evidence: [catalog/prd-release-2026-11-13.json](catalog/prd-release-2026-11-13.json). A bounded post-release log scan from 10:15:58–10:18:24 UTC found zero `request_failed` or `socket hang up` entries; this is not continuous monitoring.
