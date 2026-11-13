# PRD implementation and verification checkpoint

13 November 2026. Current application commit: `b317cefc3bfab3824f2d8388abe91965f2190531`. The selected Vercel frontend and Render Free backend use the same application release; Supabase remains the database. No paid service was added and `main` was not merged or repurposed.

## Evidence

- [PR #18](https://github.com/manavv28/restaurant-management-system/pull/18): PRD concierge, research, tiers, claims, QA and test-only voucher implementation.
- [PR #19](https://github.com/manavv28/restaurant-management-system/pull/19): remove citywide coverage aggregation from verdicts, covering indexes, source candidate/partial-refresh fixes and presentation refinements.
- [PR #20](https://github.com/manavv28/restaurant-management-system/pull/20): keep blocking research publication off the API loop, retain map visibility during search and redact research paths from API failure logs.
- [PR #21](https://github.com/manavv28/restaurant-management-system/pull/21): selectable top-three restaurant/dish/price/distance verdict and explicit parsed query scope; menu opens directly from the map sheet.
- [Full release integration](https://github.com/manavv28/restaurant-management-system/actions/runs/43407550923): 216 backend passes plus one native-PDF skip, 35 browser journeys, migration/transfer checks, production frontend/Docker builds and non-root database smoke.
- [Public release verification](https://github.com/manavv28/restaurant-management-system/actions/runs/43407550899): actual public catalogue/concierge/API checks with certificate verification enabled.
- Render deployment `dep-dbre5q0u01pc73avurj0` is LIVE. Vercel deployment `dpl_3o4YwdQjUmtWLRjXcNL17zVa3cA3` is READY on the selected production alias.
- Twelve checksummed migrations; 10,404 real venues, 357,694 available menu prices across 2,613 venues, 8,747 contacts, zero fictional samples. Post-research declared dietary labels: 368. No dataset-completeness assertion follows from these counts.
- Specific warm original-brief query: 15 matches within ₹300/2 km; median verdict 1.9 seconds across five sequential probes. This is not a p95, cold-start or 100-user certification; first-event median 835 ms exceeded that PRD target in the test network.
- Real public menu refreshes 78–83 succeeded. Post-fix jobs 81–83 completed while concurrent health/status polling stayed HTTP 200. Synthetic publication and merchant tests are documented separately and never presented as actual provider/merchant approvals.

## Explicit limits

The full requirement mapping is [PRD_TRACEABILITY.md](PRD_TRACEABILITY.md). The current [completion checklist](COMPLETION_CHECKLIST.md) identifies missing data, model/provider keys, real microphone/WER and performance evidence, a real administrator/merchant, gateway callbacks, mailbox/incident delivery, protected production restore and P1/P2 work.

Both provider MCP flags are disabled after actual whitelist/OTP failures. Browse links are available; authenticated provider prices and all-Mumbai menu completeness are not claimed. A working local text parser is not a verified live model, browser speech mocks are not phone ASR evidence, signed gateway fixtures are not an actual sandbox payment, and an isolated public-data restore is not a protected production recovery.
