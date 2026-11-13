# November 2026 audit fixes

This release builds on production commit 64502c7. It does not replace the real catalog with samples or reset data.

## Implemented

- Exact dish phrases exclude related snacks (for example pizza puff, pizza pocket and pizza sandwich). Filtering happens before each venue's cheapest eligible item is chosen.
- Known dish/cuisine pairs use dish evidence rather than incomplete venue cuisine tags. Broad discovery excludes common bottled-water brands and standalone accompaniments.
- Search responses identify GPS versus an area centre. The UI displays that origin, synchronizes budget/radius/location controls and provides an editable constraint form.
- Mobile search is reachable in the first screen; card artwork is compact and provenance/availability details expand on request. Final-total uncertainty remains visible.
- Phone/tablet overflow and small primary tap targets are addressed; search and editor inputs use 16px text on phones.
- Coverage includes source-priced menu counts by assigned locality and number-format mobile/landline/unclassified counts. These are catalog coverage measures, never a census or proof a number is active.
- Collection scheduling prioritizes menu gaps and recent locality demand without bypassing provider cooldowns. A failed candidate menu link no longer prevents checking subsequent approved links.
- Agent Wall exposes stale/failed collection alerts and records the actual parser used, rather than treating a configured but failed model as a successful model execution.

## Verified existing flows

Isolated browser journeys cover restaurant onboarding, menu editing, campaign creation, account sessions, consent, supported voice adapters/fallbacks and GPS allow/deny. Backend tests cover discount caps, meaningful-query deduplication, payment signature validation, replay protection, refund/dispute adjustments, test-money separation and ownership boundaries. Browser payment tests use explicit fixtures, not real charges or a live gateway.

## External completion gates

- All Mumbai restaurants/menus/mobile numbers: a complete census is not established. The existing licensed-source collection and import tools remain available; missing menus require permitted source observations and identity review. Invalid source/branch evidence must not be accepted merely to raise coverage.
- Always-on collection: a sleeping free web service cannot guarantee it. This patch does not buy infrastructure or change billing plans.
- Live Zomato/Swiggy comparison: existing official adapters require provider-approved access and configuration. Public search links are not price verification. No credentials or provider approvals are invented.
- AI model execution: configure a supported model through server secret settings. Deterministic fallback remains usable and is labelled accurately.
- GPay/UPI history: UPI IDs/payment intents do not grant history access. Existing consent covers BiteAI payment records only; Razorpay integration remains test-only until a separately reviewed live payment release and merchant onboarding.
- Physical devices: Chromium viewport, mocked voice recognition and geolocation tests do not verify iOS Safari/Android speech services, actual microphone capture or payment-app handoff.

No schema migrations or production data edits are required by this patch.
