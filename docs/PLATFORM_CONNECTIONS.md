# Zomato and Swiggy account connections

BiteAI uses official MCP endpoints rather than undocumented consumer APIs. The user reported approval for both integrations. Live discovery verified both providers' OAuth metadata and unauthenticated HTTP 401 challenges; public client registration accepted BiteAI's callback request (Swiggy 201, Zomato 200). Registration is not proof that end-user login, data access or price comparison succeeded.

## What is implemented

- Zomato: account-specific OAuth/PKCE, encrypted token storage, disconnect and background retrieval of the authenticated tool contract. Live restaurant/menu calls remain pending verification against that contract after a real account connects. No tool names, price units or successful live results are invented.
- Swiggy: account-specific OAuth/PKCE, rotating refresh tokens, disconnect and read-only restaurant/menu calls. Only open restaurants with a reported delivery distance inside the selected radius are offered; the user selects a restaurant before a menu request. Cart, order, payment, address and history tools are not exposed.
- Both: one-use, five-minute, session-bound connection state; per-account isolation; no tokens in browser storage; no-cache callbacks; query strings redacted from application access logs. AES-256-GCM binds stored tokens and PKCE verifiers to their user and provider and protects them with a domain-separated key derived from the existing backend JWT_SECRET. Rotating that secret requires reconnecting accounts.
- Tokens are removed on disconnect and rejected after their 30-day retention deadline; maintenance purges expired records while Render is awake. Swiggy remote logout is attempted. Zomato publishes no revocation endpoint in the observed metadata, so disconnect removes local access and instructs the user to revoke provider-side access if needed.
- Public UI offers direct platform links with the current craving. Provider-only data stays out of the public restaurant lake and analytics. Tool schemas are private configuration metadata, not restaurant exports.

## Activation and account consent

The existing Render Free service remains the backend; Supabase remains the database. Apply `20261112202617_provider_connections.sql` before deploying the compatible backend.

The exact callback URLs requiring provider approval are:

- `https://restaurant-management-system-qxtx.vercel.app/api/platforms/swiggy/callback`
- `https://restaurant-management-system-qxtx.vercel.app/api/platforms/zomato/callback`

For localhost development use the equivalent `http://localhost:3000` URLs and set PUBLIC_APP_URL accordingly. Public OAuth clients register dynamically; no consumer password or OTP belongs in BiteAI or chat. Each user signs in to BiteAI, opens **Check Zomato and Swiggy**, and connects their own provider account. Authentication and OTP entry happen on the provider's domain.

Render settings: `SWIGGY_MCP_ENABLED=true` and `ZOMATO_MCP_ENABLED=true`. Production also requires `SWIGGY_MCP_PRODUCTION_APPROVED=true` / `ZOMATO_MCP_PRODUCTION_APPROVED=true`, set only for the approved app. Defaults remain disabled in the example configuration. These settings are merged through the Render API; Blueprint files do not define or overwrite them.

`SWIGGY_MCP_PRICE_UNIT` defaults to `unknown`. Set `rupees` or `paise` only after confirming the authenticated provider contract. Ambiguous price units, variants/add-ons, unknown stock and missing amounts never become confirmed budget matches. Fees/taxes remain external-platform totals. Connection is not a declaration of working live price comparison.

The user's approvals authorize the connection work; they do not establish a bulk-catalogue licence. Swiggy's public contract restricts catalogue export and unrelated analytics. Continue using permitted public datasets for the central catalogue unless a separate agreement grants storage/export rights.

## Original requirements still requiring evidence

- Complete Mumbai inventory and priced-menu coverage: current dataset is partial.
- Actual user OAuth login and authenticated read checks on both providers; Zomato business-tool mapping after authenticated schema retrieval.
- Live AI model calls: securely configure GEMINI_API_KEY. Rules-based search remains available without it; unsupported dietary exclusions are not inferred as verified filters.
- Actual microphone transcription on a supported user device.
- Merchant onboarding, test gateway credentials and capture/refund/dispute checks before real spending-based discounts.
- Protected production backup/restore and incident-email delivery confirmation.

## Official references

- [Zomato MCP manifest and third-party access restrictions](https://github.com/Zomato/mcp-server-manifest)
- [Swiggy developer onboarding](https://mcp.swiggy.com/builders/docs/start/developer/)
- [Swiggy delegated OAuth](https://mcp.swiggy.com/builders/docs/start/enterprise/delegated-auth/)
- [Swiggy data handling](https://mcp.swiggy.com/builders/docs/operate/data-and-compliance/)
- [Swiggy access and export limits](https://mcp.swiggy.com/builders/docs/operate/access/)

## Provider login failures observed, 13 November 2026 (India)

The user's Swiggy login screenshot explicitly reports: “Oops, Vercel isn't whitelisted yet. This client isn't supported for Swiggy MCP sign-in yet.” Dynamic registration acceptance did not establish authorization for this deployed client. Prior user-reported approval remains recorded, but effective production whitelisting is unverified and Swiggy is blocked. Do not disguise this client as another supported client or substitute another application's redirect URL.

Zomato's provider-hosted OTP screen reports “Invalid request data.” This screenshot does not identify a confirmed root cause. Current OAuth metadata advertises the configured authorization/registration endpoints, `mcp:tools`, S256 and public-client authentication (`none`); no mismatch was found in these advertised parameters. Zomato's public manifest separately requires explicit callback whitelisting and provider discussion for third-party app integration. A failed OTP screen is not evidence of a successful account connection. Do not request OTPs or consumer credentials in chat or trigger additional OTP sends for diagnosis.

Provider support must verify the deployed app's exact callback/client registration and effective access. See [PROVIDER_ACTIVATION.md](PROVIDER_ACTIVATION.md) for a ready-to-copy request. Nothing was submitted to either provider on the user's behalf.
