# Architecture & trust boundaries

Browser -> same-origin Next.js /api rewrite -> FastAPI -> SQLAlchemy -> SQLite (local) or PostgreSQL (Supabase).
Custom Argon2 password authentication and expiring HS256 JWTs protect account APIs. Tokens live in sessionStorage; production should adopt secure HTTP-only cookies and CSRF protection or managed auth. Frontend does not connect directly to Supabase.

## Search workflow
1. Structured Gemini intent extraction when configured; validated deterministic rules fallback is visibly labelled.
2. Location tool resolves one of five Mumbai area centres or explicit Mumbai GPS coordinates.
3. Menu tool queries available items under the budget, then matches cuisine/dish.
4. Haversine distance tool enforces radius. Price/distance weighted ranking runs in code.
5. Discount tool evaluates persisted activity, verified spending/visits, campaign dates and prior reservations.
6. Search, result count and execution trace persist. No coordinate history is stored.

No LLM is called when GEMINI_API_KEY is absent. These are composable workflows with real tools, not autonomous internet scraping agents. Missing cuisine/dish prompts a follow-up; defaults for budget and radius remain explicit in UI.

## Ingestion workflow
Owners submit permission-confirmed menu JSON. Pydantic validates shape, name whitespace is normalized, case-insensitive dish matching updates existing records, and old/new price values persist in an ingestion log. New data remains unverified. Google Places discovery is an optional authenticated, on-demand API call; returned provider content is not persisted indefinitely. Respect provider licence/retention/attribution rules before adding storage. No Zomato/Swiggy scraping, live menu claims or automatic business-ownership verification.

## Financial calculations
Amounts are integer paise. Discount = min(order_paise * percent // 100, cap). Search counts never contribute to spend. Simulation creates only explicitly simulated transactions, excluded from spend/visit eligibility. Reservation is not settlement. Per-user row locks (PostgreSQL) and unique reservation sequence constraints prevent duplicated redemption limits. Live webhook intentionally returns 501 until a gateway-specific signature-verification adapter is implemented.

## Privacy and operations
Restaurant endpoints enforce account role and row ownership. Restaurant analytics expose aggregate clicks/campaigns only, never personal query history. Personal history is deletable. Consent can be withdrawn; new payment simulation then fails. Daily retention job removes search/interaction records older than 30 days, payment summaries/reservation audits after 365 days. Set real retention requirements before deployment. API logs should never include passwords, bearer tokens, provider keys or full request bodies.

Supabase migration enables RLS and revokes direct anon/authenticated access. Use a private backend DB role; never expose database URL or JWT signing key to a browser. Production hardening gates are in IMPLEMENTATION.md.
