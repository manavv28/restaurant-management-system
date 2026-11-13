# Audit follow-up validation

Validation used isolated SQLite and PostgreSQL 17 fixtures, never the production
restaurant database or real payment accounts.

- Full PostgreSQL backend suite: **258 passed**, including migrations, schema
  constraints, source ingestion, provider fixtures, query rewards, payment
  signatures/replays/refunds and the new search regressions.
- After moving public artifact storage out of the web authentication module,
  the affected catalogue/search suite passed again: **42 passed**.
- Browser suite: **48 cases exercised**. The full run passed 47; the provenance
  case was updated to expand the new source-details control and then passed.
  Focused reruns also verified the final 390px Hindi-query/menu flow and mobile
  navigation/filter controls at 320, 390 and 430px.
- Production Next.js build, TypeScript checks and `git diff --check` passed.
- The new migration was applied to an isolated PostgreSQL database. The migrated
  constraint accepts `vegan,gluten-free` and rejects an unsupported `healthy` claim.
- An in-flight initial search was deliberately held while changing budget scope;
  its response no longer replaces the user's selection.

Browser checks cover customer registration/session/consent, owner listing/menu/
campaign creation, provider availability, checkout callbacks using explicit
fixtures, voice adapters/fallbacks, GPS allow/deny, maps/markers and responsive
layout. Street tiles were unavailable in the headless test network; the marker
and fallback explanation remained usable. Live speech, physical iOS/Android,
approved provider reads and real payment settlement remain unverified.

The live site and catalogue were not deployed or modified by these local checks.
Rollout order and outstanding setup are in [audit fixes](AUDIT_FIXES.md).
