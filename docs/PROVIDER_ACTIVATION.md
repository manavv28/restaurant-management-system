# Provider activation request details

Prepared 13 November 2026 (India). These are drafts for the provider approval/support channels; no request has been sent. Do not include passwords, OTPs, authorization codes, state values, tokens or customer phone numbers.

## Swiggy

BiteAI is deployed at https://restaurant-management-system-qxtx.vercel.app and uses the official food MCP endpoint https://mcp.swiggy.com/food with OAuth PKCE S256 and dynamic public-client registration. The provider sign-in page rejects the deployed client with “Oops, Vercel isn't whitelisted yet. This client isn't supported for Swiggy MCP sign-in yet.” Please confirm or activate production access for BiteAI and whitelist this exact callback:

`https://restaurant-management-system-qxtx.vercel.app/api/platforms/swiggy/callback`

Please also confirm whether approval uses the exact redirect URL, deployment domain, or a stable provider-issued client ID, and supply the supported onboarding configuration through the approved secure channel. Current requested scope is `mcp:tools`; use is restricted to user-consented restaurant/menu browsing. We do not need cart, order or payment tools for this integration.

Use “Request access on Builders Club” or the provider's GitHub request link shown on the Swiggy error page. Reference: https://mcp.swiggy.com/builders/docs/start/developer/

## Zomato

BiteAI uses https://mcp-server.zomato.com/mcp with OAuth PKCE S256, scope `mcp:tools` and public-client registration. Its provider-hosted OTP screen reports “Invalid request data.” Please investigate the sign-in request and verify third-party integration approval and exact redirect whitelisting:

`https://restaurant-management-system-qxtx.vercel.app/api/platforms/zomato/callback`

Please confirm whether a stable approved client registration is required instead of dynamic registration. Do not send access tokens, OTPs or customer credentials through the support request. A sanitized screenshot and approximate failure time can be supplied.

Official access form: https://forms.eternal.com/form/ja8hap2tpm
Manifest and current restrictions: https://github.com/Zomato/mcp-server-manifest

## After provider confirmation

Apply any provider-issued client configuration securely, keeping secrets server-side; then start a fresh connection from BiteAI in the same browser/session. Verify the callback and authenticated tool schema before claiming live restaurant/menu reads. Zomato mapping and Swiggy price-unit confirmation remain pending. Never bypass whitelisting with another app's name, credentials or callback.
