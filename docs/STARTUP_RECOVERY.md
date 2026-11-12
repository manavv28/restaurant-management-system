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
