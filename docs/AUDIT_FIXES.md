# Audit fixes and deployment gates

This change starts from the audited `deploy/biteai-mvp` release `518ad6c`.
It prepares source fixes; it does not claim the public deployment or its data has
already changed. The owner confirmed that no AI, delivery-platform or payment
provider account is currently approved/configured for this work.

## Implemented

- Parse `300 rupaye mein`, Devanagari digits and spoken price amounts without
  treating a party size or distance as a rupee limit.
- Validate model proposals, then preserve explicit budgets, distance, location,
  dietary requirements, exclusions, party size and budget scope. A model cannot
  replace an unsupported location with Bandra.
- Return a complete clarification response for unresolved places. Both JSON and
  streamed search paths retain the requested place, skip catalogue/research
  substitution, and persist the clarification without issuing query reward credit.
- Match all explicit dietary declarations together, including vegan/gluten-free.
  Unknown declarations do not satisfy a request. Owners can declare these labels;
  labels remain owner/source declarations, not independently verified ingredients.
- Add per-item/total budget controls and preserve edits made while an older search
  is pending. Group subtotals still identify unconfirmed fees and portions.
- Preselect the owner role from restaurant registration and preserve that intent
  across the sign-in/signup switch.
- Add compact phone navigation, 44px map microphone targets, scrollable filter
  panels with a Done action, and more readable expandable menu provenance.
- Put the searched dish first in the restaurant menu; choose fallback food art
  from the dish rather than an incomplete restaurant cuisine label.
- Keep original price observation age separate from retrieval and preserve source
  metadata for above-budget alternatives. Old reference prices remain labelled.
- Stop automatic retry storms for invalid evidence, identity conflicts and denied
  source access. Transient failures retain backoff; review failures retain a
  minimum 24-hour cooldown. Expired worker leases are recovered atomically.
- Expose low-coverage collection priorities and add bounded collection batches
  that can run independently of the sleeping web service.

## Migration and rollout order

1. Back up the existing production database using the configured operator process.
2. Apply `supabase/migrations/20261113173000_declared_dietary_labels.sql` through
   the existing migration runner. It widens the declaration column and expands
   its check constraint without rewriting existing declarations or granting access.
3. Deploy the backend from this change. Existing clients remain compatible.
4. Deploy the frontend with the existing `API_INTERNAL_URL`. Preserve database,
   authentication, mail and provider settings. Do not enable payment simulation
   or fictional seeds in production.
5. Verify the live release, Hindi budget query, unsupported-location clarification,
   owner signup and mobile controls. The tests in this change run on isolated data.

The new frontend sends an optional `budget_scope` field. Deploy the backend first
so the control has its intended effect. Roll back the application without narrowing
the dietary column: existing old declarations remain valid under this migration.

## Collection outside Render Free uptime

The existing web-service worker remains compatible. An external scheduler can run:

```sh
PYTHONPATH=backend python -m app.catalog_worker --batch --max-jobs 100 --max-seconds 600
```

This schedules **existing enabled, reviewed sources only**. It does not add new
sources, change permissions, bypass robots/access restrictions, scrape restricted
platforms or synthesize missing menus. Atomic job claims prevent duplicate work
with the web-service worker. Backoff and source-review cooldown remain authoritative.
The time budget stops starting new work; an in-flight bounded source request can
finish. A nonzero exit means a failure, retry or review is pending.

`.github/workflows/catalog-refresh.yml` supplies an hourly bounded scheduler using
the deployment branch. To activate it, put the workflow on the repository's default
branch, configure the `production-catalog` environment, and supply the server-only
`CATALOG_DATABASE_URL` secret through secure configuration. The collection runner
does not need the web application's JWT secret or provider account tokens. Do not
rotate working values or paste them into chat. Set approved host variables from the operator's
reviewed list. An optional `GEMINI_API_KEY` enables extraction only when supplied.
The workflow fails clearly before collection if required settings are absent.

No scheduled production run or new catalogue coverage is claimed by committing
this workflow. Expanding coverage still requires reviewed sources, provider access
and successful collection into the live database. `is_complete: false` remains
explicit; a complete Mumbai denominator has not been established.

## Still external or unverified

| Capability | Remaining prerequisite |
|---|---|
| Live AI reasoning/extraction | Configure Gemini credentials or a reachable operator-hosted model; run credentialed verification. The deterministic fallback remains accurately labelled. |
| Zomato/Swiggy reads | Provider approval and schema/price-unit verification; authenticate through the provider. Do not bypass the existing whitelist/OTP blocks. |
| Payment-backed discounts | Onboard a merchant, configure sandbox keys/webhook and restaurant mapping, then exercise actual authorized sandbox capture/refund/redemption. Fixtures do not establish provider certification. |
| Wider payment history | A supported consent-based data provider is required. A UPI ID supplies no account history; no GPay credentials or UPI PINs are collected. |
| Complete Mumbai data | Expand and verify permitted sources and branch identities; measure completeness against a dated baseline. Missing facts remain missing. |
| Scheduled production collection | Activate a scheduler with securely configured database/worker access; verify real run results and source health. |
| Physical mobile behavior | Test real Android/iOS audio, GPS, keyboard, install and payment-return flows. Automated viewport/adapter tests do not certify physical devices. |

See `docs/REQUIRED_CONFIGURATION.md`, `docs/PROVIDER_ACTIVATION.md` and
`docs/PAYMENTS.md` for the existing provider activation contracts.
