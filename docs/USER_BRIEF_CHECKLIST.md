# Remaining work against the user's original BiteAI brief

Verified 13 November 2026 (India), application release `b317cefc3bfa`. This checklist separates working software from actual coverage and live-provider evidence. It does not certify full production readiness.

## Voice/text food discovery

- [x] Text search, Mumbai area/GPS selection, budget and radius filtering, ranking, restaurant details and menus.
- [x] Browser voice controls and text fallback, including automated voice-adapter tests.
- [ ] Actual microphone transcription on a supported user phone/browser.
- [ ] Live AI interpretation: add GEMINI_API_KEY securely in Render and verify a real structured model response. Hinglish/Devanagari rules, context, explicit dietary and supported-hour filters work; a key cannot supply unknown menu facts.

## “All restaurants, menus and mobiles in Mumbai”

- [x] Central relational catalogue, location indexes, source attribution, freshness and explicit unknown values.
- [x] Full available public-source scan checked 54,422 source listings; reviewed priced menus were published.
- [ ] Complete restaurant coverage: 10,404 source-backed listings are present, but no exhaustive Mumbai census is established.
- [ ] Complete menu coverage: 357,694 source-listed prices across 2,613 restaurants. The remaining 7,791 listings lack usable priced menus.
- [ ] Complete public-contact coverage: 8,747 listings have contact numbers; 1,657 remain missing. Numbers are source observations, not independent confirmations.
- [ ] Continue resolving ambiguous names, branches, contacts, closed businesses and stale menus as reliable sources become available.

## Zomato and Swiggy

- [x] Contextual platform-browsing links and per-match search links are available; external current prices/availability are checked on those websites.
- [x] Official endpoint/OAuth spike and encrypted per-user adapter implementation are retained but disabled in production after actual Swiggy whitelist and Zomato OTP failures. Cutting this optional spike follows the uploaded PRD.
- [ ] Provider-side approval/working consent, authenticated schema/units verification and Zomato menu mapping before enabling account reads. A callback registration or reported connection does not prove an actual account read; none is claimed.
- [ ] Any bulk catalogue export/storage needs the applicable provider agreement. Browse links do not import platform menus into the lake.

## Agents do the busywork

- [x] Functional discovery, ingestion, cleaning, deduplication, menu/price processing, location/ranking, discount tools and execution traces.
- [x] Checkpointed public menu/contact collectors and protected, replayable publication. Scheduled menu refresh runs while Render Free is awake.
- [ ] Expand ongoing citywide discovery/enrichment and exception resolution beyond the available sources. Free service sleep and source access limits prevent an always-on completeness guarantee.
- [ ] Live model-powered workflows await the model credential and provider/account verification above.

## Custom discounts based on searches or spending

- [x] Restaurant portal, claims/review, owner-approved offer copilot, tiers, unique-query credits, cuisine conditions, weekly/daily budgets and auditable eligibility.
- [x] Test-only signed capture, QR vouchers and once-only redemption/refund/dispute logic; sandbox amounts never increase verified real spend.
- [x] Payment-data consent, withdrawal and authorised gateway/webhook architecture; purchase history is not inferred from searches.
- [ ] Actual merchant onboarding, gateway test credentials and verified capture/refund/dispute tests before real spending-based offers.
- [ ] Validate real campaigns/redemptions with participating restaurants.
- [ ] Direct access to a user's complete GPay history is not implemented or assumed. Use authorised consent-based transaction verification; never collect UPI PINs, payment passwords or OTPs.

## Central data lake

- [x] Initial public catalogue, own searches/results, preferences, interactions, offers, transaction summaries, provenance and workflow traces with access controls and retention.
- [ ] Provider-account response storage/analytics beyond the immediate user task needs the applicable rights and consent. MCP responses are currently kept out of the public catalogue and analytics.

Operational follow-ups such as encrypted production recovery and incident-alert delivery are separate launch safeguards in [STATUS.md](STATUS.md). Details and evidence: [PLATFORM_CONNECTIONS.md](PLATFORM_CONNECTIONS.md), [PUBLIC_CONTACTS.md](PUBLIC_CONTACTS.md) and [the release report](catalog/provider-contacts-2026-11-13.json).

## Presentation and release verification

- [x] Consistent styled controls, clear provider connection badges, responsive directory results, readable mobile cards, visible keyboard focus and request/disabled states.
- [x] Latest hosted validation: 216 backend tests plus one PDF skip, 35 browser journeys, production builds, migrated database smoke and three public-release checks.
- [x] Original Haka-noodles/₹300/2 km request verified against the public catalogue, with source attribution and explicit reference-price limits.

These completions do not change the open data/integration requirements above. See [IMPLEMENTATION_VERIFICATION.md](IMPLEMENTATION_VERIFICATION.md).

The uploaded PRD adds further targets and P1/P2 scope. See [PRD_TRACEABILITY.md](PRD_TRACEABILITY.md) and the current [completion checklist](COMPLETION_CHECKLIST.md); neither exhaustive coverage nor every PRD verification is complete.
