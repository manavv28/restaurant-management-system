# Free discovery and reliability release

This release requires no Zomato/Swiggy permissions, paid API keys, new database
schema, new hosting resource, or paid plan. It preserves the existing live
catalog and existing owner/reward/payment adapters.

## Implemented

- Deterministic Hinglish exclusions, party-size parsing, contextual constraints,
  walking-distance caveats, and explicit area precedence over stale GPS.
- Total-budget filtering uses one item per person as an explicit assumption;
  portions are not inferred. Every result exposes a unit price, subtotal,
  eligible single-item offer preview, unknown fees, and an unconfirmed payable
  total. Combined alternative menu names are excluded from exact dish matches.
- Optional local Ollama structured intent extraction, schema validation and a
  four-second timeout with transparent deterministic fallback. Gemini's existing
  optional extraction now receives the complete intent schema.
- Exponential worker backoff with numeric/HTTP-date Retry-After support,
  longer cooldown for extraction/access/identity failures, worker-cycle recovery,
  aggregate public source-health diagnostics and admin-only reviewed retries.
  Demand-triggered research observes failed-source cooldowns too.
- Results precede coverage, directory and recommendation panels. Generic searches
  exclude common bread/condiment-only items; ranking uses distance/price/rating.
- Catalog shows menu coverage within imported records and remaining unpriced
  listings. No citywide-completeness claim. Dates render in India time.
- Platform links explicitly disclose that live quotes have not been compared.
  Official integrations stay disabled unless separately approved/configured.
- Consent explains scope, 365-day payment audit retention and withdrawal. Query
  offers do not require payment consent. Password recovery moved into sign-in,
  while emailed reset/verification links still work without opening sign-in.
- Existing owner campaign rules, query deduplication, spend/refund handling,
  ownership isolation and voucher safeguards retained and regression-tested.

## Free local model setup (optional)

Follow https://docs.ollama.com/api/chat and install Ollama on your own machine
with sufficient resources; run `ollama pull qwen3:1.7b`. For a co-located local
backend set `OLLAMA_URL=http://127.0.0.1:11434` and
`OLLAMA_MODEL=qwen3:1.7b`. Restart the backend. No cloud account/API key is needed.
For remote hosting, a secure reachable model service is still required; do not
expose an unauthenticated Ollama API publicly. Render Free is not provisioned
with a model, and this change does not claim that it is.

## Explicit limits

- No automatic Zomato/Swiggy live quote comparison or private account scraping.
- No GPay/UPI history access. A UPI ID is not a transaction feed. Existing
  gateway-verified spending requires a configured provider and merchant onboarding.
  User-entered/simulated amounts never become verified spend.
- No guarantee of all Mumbai restaurants, current prices, portions, live opening
  status, walkable routes, or delivery serviceability.
- Background work remains subject to free-host sleep and quota limits. Historical
  failed jobs are retained; retries do not silently revalidate stale menu evidence.
- Public source health is aggregated; detailed errors/retries require admin auth.
- Raw source artifacts remain bounded (50, max 1 MB each, seven-day retention).
  Normalized provenance/evidence remains separate; this is not unlimited storage.

## Verification

Run backend tests, frontend production build/typecheck, and Playwright against
an isolated local database. PostgreSQL-only migration/concurrency tests require
CI PostgreSQL and are skipped by the SQLite run. Do not run mutation-based
browser journeys against production.
