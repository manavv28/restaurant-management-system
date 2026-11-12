# Remaining work against the user's original BiteAI brief

Verified 13 November 2026 (India), application release `3678a24e8044`. This checklist separates working software from actual coverage and live-provider evidence. It does not certify full production readiness.

## Voice/text food discovery

- [x] Text search, Mumbai area/GPS selection, budget and radius filtering, ranking, restaurant details and menus.
- [x] Browser voice controls and text fallback, including automated voice-adapter tests.
- [ ] Actual microphone transcription on a supported user phone/browser.
- [ ] Live AI interpretation: add GEMINI_API_KEY securely in Render and verify a real structured model response. Rules-based extraction currently works; enabling a key does not add unsupported dietary data or filters.

## “All restaurants, menus and mobiles in Mumbai”

- [x] Central relational catalogue, location indexes, source attribution, freshness and explicit unknown values.
- [x] Full available public-source scan checked 54,422 source listings; reviewed priced menus were published.
- [ ] Complete restaurant coverage: 10,404 source-backed listings are present, but no exhaustive Mumbai census is established.
- [ ] Complete menu coverage: 357,694 source-listed prices across 2,613 restaurants. The remaining 7,791 listings lack usable priced menus.
- [ ] Complete public-contact coverage: 8,747 listings have contact numbers; 1,657 remain missing. Numbers are source observations, not independent confirmations.
- [ ] Continue resolving ambiguous names, branches, contacts, closed businesses and stale menus as reliable sources become available.

## Zomato and Swiggy

- [x] Official endpoint research, observed OAuth metadata/401 challenges and successful callback client registration requests.
- [x] User-reported approvals recorded; deployed per-user connection/disconnect controls and encrypted credential storage.
- [x] Read-only Swiggy restaurant/menu adapter, selection-bound menu requests, stock/radius checks and safe unknown prices.
- [ ] Actual end-user account consent and authenticated read verification for both providers. Use the app's **Check Zomato and Swiggy** panel; enter login/OTP only on the providers' pages.
- [ ] Confirm Swiggy's actual price units before enabling budget comparisons. Unknown units and ambiguous variants remain unconfirmed.
- [ ] Validate Zomato's authenticated tool schema and finish its restaurant/menu mapping. Schema metadata is captured privately after account connection; live business search is not yet claimed.
- [ ] Any bulk catalogue export/storage requires the appropriate provider agreement. A working user-scoped MCP connection does not establish unrestricted data-lake rights.

## Agents do the busywork

- [x] Functional discovery, ingestion, cleaning, deduplication, menu/price processing, location/ranking, discount tools and execution traces.
- [x] Checkpointed public menu/contact collectors and protected, replayable publication. Scheduled menu refresh runs while Render Free is awake.
- [ ] Expand ongoing citywide discovery/enrichment and exception resolution beyond the available sources. Free service sleep and source access limits prevent an always-on completeness guarantee.
- [ ] Live model-powered workflows await the model credential and provider/account verification above.

## Custom discounts based on searches or spending

- [x] Restaurant portal, campaigns, query-count/spend eligibility, limits, validity, redemption tracking and auditable calculations.
- [x] Payment-data consent, withdrawal and authorised gateway/webhook architecture; purchase history is not inferred from searches.
- [ ] Actual merchant onboarding, gateway test credentials and verified capture/refund/dispute tests before real spending-based offers.
- [ ] Validate real campaigns/redemptions with participating restaurants.
- [ ] Direct access to a user's complete GPay history is not implemented or assumed. Use authorised consent-based transaction verification; never collect UPI PINs, payment passwords or OTPs.

## Central data lake

- [x] Initial public catalogue, own searches/results, preferences, interactions, offers, transaction summaries, provenance and workflow traces with access controls and retention.
- [ ] Provider-account response storage/analytics beyond the immediate user task needs the applicable rights and consent. MCP responses are currently kept out of the public catalogue and analytics.

Operational follow-ups such as encrypted production recovery and incident-alert delivery are separate launch safeguards in [STATUS.md](STATUS.md). Details and evidence: [PLATFORM_CONNECTIONS.md](PLATFORM_CONNECTIONS.md), [PUBLIC_CONTACTS.md](PUBLIC_CONTACTS.md) and [the release report](catalog/provider-contacts-2026-11-13.json).
