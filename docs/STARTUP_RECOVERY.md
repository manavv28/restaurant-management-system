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
