# Search startup and coverage recovery — 12 November 2026

A user reported `Unexpected token '<'` from a search response and an old zero-price coverage panel. A live search probe initially timed out after 45 seconds. Subsequent health and coverage responses were valid JSON and showed the expected release and all 91 unexpired source observations in Supabase. No recent Render server-failure event was found. The behavior is consistent with startup/proxy HTML being parsed as JSON while the Free backend wakes; the screenshot does not identify the exact HTML producer.

The previous client parsed every response as JSON and loaded coverage only once. The fix:

- Validates JSON responses, bounds request waiting and displays useful errors instead of raw parser/HTML text.
- Checks read-only health before submitting a search. Transient startup failures retry within a 90-second readiness budget, with a visible waiting status. Concurrent readiness checks share one promise, with a short readiness cache while active.
- Sends each search POST once. Failed/uncertain POST responses are not automatically replayed.
- Suppresses older search responses and loading/error updates when a newer search has begun.
- Defers initial account reads until health succeeds, avoiding a false signed-out state during startup.
- Refreshes coverage after successful search, on tab focus/visibility and on explicit retry. Aborted or superseded coverage responses cannot replace newer data. Unavailable coverage is not displayed as fabricated zeros.

There is no background keep-alive or hosting-plan change. Render Free can still sleep and require startup time. Supabase, publisher snapshots, email settings and API authentication are unchanged.

Validation before release: all 17 local Playwright tests passed, including simulated HTML cold-start responses, delayed health readiness, single search submission, useful HTML-error feedback, stale-zero coverage refresh, and existing account/consent/location/checkout journeys. The Next.js production build/TypeScript checks passed. Hosted CI and deployment verification are recorded after release.

## Deployed verification

PR #9 is merged. Release `25cd602bb39e91880d91fe8eb295f63a250a5f9e` is live on the selected Vercel frontend and Render Free backend. [Hosted integration run 43205988098](https://github.com/manavv28/restaurant-management-system/actions/runs/43205988098) and [public mobile-browser run 43205988068](https://github.com/manavv28/restaurant-management-system/actions/runs/43205988068) passed. All 17 browser tests passed locally with two workers and in hosted CI, with production build/typecheck and Docker/image smoke verification. The map restaurant list is memoized so unrelated startup/account/query-input updates preserve the open popup; a regression test exercises that behavior.

Both public API origins report 91 fresh source observations and return Spicy jackfruit dumpling at ₹595 for the exact screenshot query, “Find spicy jackfruit dumpling under 1000 in Bandra”. The public JavaScript build contains the new startup handling. Existing email availability remains enabled, Supabase uses verify-full TLS, and no data or credentials were changed for this fix. The publisher's separate HTTP 403 refresh limitation and original snapshot expiry remain unchanged.

An already-open page needs one refresh to load the new client code. Future focus/visibility and successful searches refresh coverage without a page reload. Free-service startup can still take time; the UI waits and reports unavailable responses safely rather than displaying a raw JSON parser error.

## Readiness timeout and false empty state — 12 November 2026, 17:26 UTC

The user confirmed the selected production URL and supplied a screenshot showing a readiness timeout alongside “No matches just yet.” The client had set its completed-search flag before readiness or the POST succeeded. This was a connection failure displayed as a zero-result search. During diagnosis, both live health origins returned valid JSON in under one second, catalog reads succeeded, and Render reported no recent server-failure event. The original end-user transport failure was not reproduced; a cold start is not established as its cause.

Release `086e67bbd4718aa377fd0e7d527821aa630b8031` separates connection errors from valid empty searches. It shows an inline Retry search action, preserves any previous results with a label, and suggests no fictional data. A successful catalog/database read can establish readiness when the health probe is unavailable. Search POSTs remain single-attempt operations; retrying requires the user's explicit action. Account refresh no longer delays completion of an otherwise successful search.

A dedicated dynamic `/api/health` handler fetches the configured upstream with a bounded timeout, preserves valid connected-health JSON, normalizes warm-up HTML/invalid JSON/network failures to JSON 503, and sends `Cache-Control: no-store, max-age=0` for both outcomes. No schema or infrastructure-plan changes were required.

[Integration run 43272042476](https://github.com/manavv28/restaurant-management-system/actions/runs/43272042476) passed 78 backend checks with one existing native-PDF skip, 23 browser/helper checks, the frontend build and actual Docker/database smoke test. [Public browser run 43272042141](https://github.com/manavv28/restaurant-management-system/actions/runs/43272042141) passed. Additional checks against the production origin forced failed health probes with a healthy catalog, then a complete 90-second readiness failure followed by restored connectivity: fallback succeeded, the failure displayed Retry rather than zero matches, and explicit retry sent exactly one search POST. Managed-executor resource fetching used the supplied proxy/CA through Playwright's TLS-validating client; certificate validation was retained.

Render deployment `dep-dbqvknqfngtc73ef8fng` is live and Vercel deployment `dpl_31Laas2qHzpjaWTv6CxcywCxG1VJ` is READY. Both API origins report release `086e67bbd471`, 10,404 real-source listings, 48 search areas, all 91 preserved menu prices, and Supabase verify-full TLS. Render remains Free. The post-deploy error-log scan was empty. Free-instance wake-up latency and end-user network failures remain possible; this release improves recovery rather than claiming those platform/network delays are eliminated.
