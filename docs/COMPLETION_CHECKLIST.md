# BiteAI implementation checklist

Updated 13 November 2026. Preserve Render Free, Supabase and the selected Vercel frontend. This checklist refers to the original brief and uploaded Bhook.ai PRD; checked software is distinct from live external certification.

## Completed software and release checks

- [x] Recover work beyond `3be2c86`, retain changes in Git and deploy only from `deploy/biteai-mvp`.
- [x] Central, attributed public catalogue with geographic retrieval, source dates, price evidence and explicit missing data.
- [x] Text/Hinglish interpretation, budget/radius constraints, follow-up context and database-only top verdict with streamed execution events.
- [x] Browser voice controls/text fallback; dark-first map concierge, polished list/portal/buttons, phone layout, reduced motion and theme controls.
- [x] Durable reviewed-source menu research, cached answer first, publication/retention and partial-success re-query; blocking research work isolated from the API event loop.
- [x] Agent Wall, administrator-only QA, pending restaurant claims with independent review and owner-approved offer suggestions.
- [x] Query/spend tiers and anti-abuse rules; daily/weekly discount budgets, amount/cuisine restrictions and auditable eligibility.
- [x] Sandbox-only signed capture/refund/dispute logic, scoped QR vouchers, once-only merchant redemption and cancellation/expiry. Sandbox spend is excluded from real-spend rewards.
- [x] Revocable secure sessions, email verification/reset implementation, CSRF/RBAC, private-table RLS, retention and sanitized capability logging.
- [x] Twelve additive, checksummed migrations applied and tested. Existing catalogue/publisher menus preserved.
- [x] PWA manifest and offline explanation that never caches account/API responses.
- [x] PostgreSQL, browser, migration/transfer, production build and Docker/image smoke checks. See [current release evidence](STATUS.md).
- [x] 126-second public-app demo recording: map, Hinglish text verdict, follow-up, real catalogue details and Agent Wall; no real microphone/payment/provider-login claim.
- [x] Contextual Zomato/Swiggy website browsing links. Blocked account-connect spike disabled in the MVP, as permitted by the PRD.

## Remaining original-brief and P0 evidence

- [ ] **Complete Mumbai venue/menu/contact coverage:** 10,404 venues are present, but 7,791 lack priced menus and 1,657 lack contacts. More usable sources and reconciliation are needed; no exhaustive census or universally current prices can be claimed.
- [ ] **Live model:** configure `GEMINI_API_KEY` securely and validate actual structured responses/quotas. The 100-case text suite validates deterministic interpretation, not live model or speech accuracy.
- [ ] **Real phone voice:** microphone permission, actual English/Hinglish transcription and the PRD's <15% WER measurement on a supported phone. Voice adapter tests are not this evidence.
- [ ] **Merchant demo:** onboard a participating restaurant, configure Razorpay test keys/webhook secret and merchant mapping, and demonstrate actual sandbox capture, QR redemption, refund and dispute callbacks. Never enable live charges without provider approval.
- [ ] **Real campaigns and claims:** provision a genuine administrator securely, independently review a merchant's business/contact evidence, then have that merchant approve a real offer.
- [ ] **Data quality:** independent spot checks for venue identity/branch, price, phone and menu-source validity; establish the PRD's 85% accuracy target. Reference menus are not independently verified publisher extractions.
- [ ] **Performance:** representative p50/p95/first-event measurements, 100-user capacity and mid-range-phone motion/interaction checks. Five warm probes had a 1.9 s median verdict; first event was 835 ms, above the 600 ms target in that network.
- [ ] **Operations:** confirm inbox verification/reset and an actual incident email; configure encrypted production backups and restore a protected production artifact into an isolated target.
- [ ] **External end-to-end demonstrations:** research/publication and merchant-offer flows using real reachable sources and an onboarded merchant. Fixture success alone is insufficient.

## P1/P2 and optional follow-ups

- [ ] pgvector/canonical-dish embeddings and semantic retrieval; current retrieval is lexical/geographic.
- [ ] Receipt OCR and consent-based Account Aggregator integration, with fraud validation. A receipt or user confirmation must not be labelled independently verified funds; a UPI ID cannot grant complete GPay history.
- [ ] Microphone-amplitude voice animation, remaining advanced transitions, richer tool/replay/billing telemetry and actual-device offline verification.
- [ ] Authenticated Zomato/Swiggy read-only integration only if provider whitelisting/OTP contract is resolved; confirm units/schema and storage rights before enabling. This is optional in the uploaded PRD; browsing links already work.

Exact nonsecret details and secret placement: [REQUIRED_CONFIGURATION.md](REQUIRED_CONFIGURATION.md). Full requirement mapping: [PRD_TRACEABILITY.md](PRD_TRACEABILITY.md). These unchecked requirements prevent a blanket claim that all instructions are met.
