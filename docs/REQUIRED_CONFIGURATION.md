# Inputs needed to finish BiteAI's live integrations

The application is deployed at https://restaurant-management-system-qxtx.vercel.app. Keep the existing Render Free backend and Supabase database. This guide lists the configuration still needed; it does not claim these services are configured or verified.

## Information you can provide in chat

1. **Discovery/menu sources:** the permitted public catalogue currently contains 10,404 listings, 357,694 source-listed prices across 2,613 restaurants and 8,747 contact numbers. Coverage remains partial. Official Zomato/Swiggy account links are deployed; the user reported approvals and both client registrations accepted callback requests, but end-user OAuth remains unverified. Use **Connect Zomato** and **Connect Swiggy** inside BiteAI; Browse links open websites and do not link accounts. See [PLATFORM_CONNECTIONS.md](PLATFORM_CONNECTIONS.md) and [USER_BRIEF_CHECKLIST.md](USER_BRIEF_CHECKLIST.md). Google Places is an optional additional discovery source, not a requirement for the existing public-source catalogue.
2. **Email sender:** selected Gmail address **letsbiteai@gmail.com**. Gmail App Password is configured, and the authenticated HTTPS relay is active. Gmail accepted the operator test; inbox receipt and actual verification/reset completion remain pending. See [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md).
3. **Alert recipient:** selected **letsbiteai@gmail.com**. Incident-alert delivery still needs an actual verified notification. The working security-mail relay does not by itself establish that a scheduled alert was delivered.
4. **Backup destination:** selected encrypted GitHub artifacts retained seven days; protected production backup/restore is still unverified. Workflow, secure secret names, recovery instructions and default-branch scheduling requirement are in [BACKUPS.md](BACKUPS.md). Keep the decryption secret separately from backup files.
5. **Payments:** identify the onboarded restaurant/merchant and whether you have a Razorpay test account. Complete legal/KYC and settlement approval directly with the payment provider before any live charging.

## Secrets to enter through secure settings

Do not paste secret values in chat, commit them, or upload a live .env file. Existing Render/Vercel connections can manage deployment settings, but they do not supply Gemini, Google, SMTP, merchant or database-backup credentials automatically.

### Render → biteai-demo → Environment

**Render Free blocks SMTP ports.** Gmail settings alone cannot deliver mail from this backend. The active authenticated HTTPS relay and its explicit activation approval are documented in [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md). The saved Gmail App Password can be reused through that server-only relay.

| Purpose | Variable | Required access/configuration |
|---|---|---|
| Gemini query/menu extraction | GEMINI_API_KEY | A key for your Gemini project, with a quota/budget you control |
| Google Places discovery | GOOGLE_PLACES_API_KEY | Server-side key with Places API (New) enabled and appropriate API restrictions |
| Email delivery | SMTP_HOST | Your provider's SMTP hostname |
| Email delivery | SMTP_PORT | 465; the current adapter uses SMTP over TLS |
| Email delivery | SMTP_USER | Provider-issued SMTP username, if required |
| Email delivery | SMTP_PASSWORD | Provider-issued SMTP password/key |
| Email sender | EMAIL_FROM | A sender address verified with the provider |
| Razorpay sandbox | RAZORPAY_KEY_ID | Test-mode key ID |
| Razorpay sandbox | RAZORPAY_KEY_SECRET | Test-mode key secret |
| Signed payment events | RAZORPAY_WEBHOOK_SECRET | The secret configured for this app's provider webhook |

PUBLIC_APP_URL is already configured as https://restaurant-management-system-qxtx.vercel.app. The app's DATABASE_URL and JWT_SECRET already exist; preserve them. Do not replace working database/authentication secrets to configure unrelated integrations.

I can set nonsecret APPROVED_MENU_HOSTS and the onboarded RAZORPAY_RESTAURANT_IDS after the approved domains and merchant/restaurant mapping are known. No arbitrary restaurant ID should be enabled for payments.

### Vercel → restaurant-management-system-qxtx → Environment

| Purpose | Variable | Required access/configuration |
|---|---|---|
| Google Maps rendering | NEXT_PUBLIC_GOOGLE_MAPS_KEY | Browser key with Maps JavaScript API enabled and HTTP-referrer restrictions for the deployed site |
| Google Maps styling | NEXT_PUBLIC_GOOGLE_MAP_ID | Your map ID, if available; optional |

The Maps browser key is intentionally public and must be restricted by referrer/API. Never put the server-side Places key, Gemini key, SMTP credentials or Razorpay secret in a NEXT_PUBLIC variable. API_INTERNAL_URL is already configured; preserve it.

Gemini/Places/Maps may require provider account setup and billing/quota decisions. No paid resource or billing upgrade is authorized by this guide. Deterministic search and Leaflet remain available until these integrations are configured.

## Payment webhook setup

Configure the provider's **test-mode** webhook to:

https://biteai-demo.onrender.com/api/payments/webhook

Supported events: payment.captured, refund.processed, payment.dispute.created, payment.dispute.won, and payment.dispute.lost. Configure the same webhook secret securely in the provider and Render. Hosted checkout stays unavailable until its provider settings and restaurant onboarding are complete. Live merchant identity and settlement approval must come from the provider; website-control verification alone does not establish either.

## Production backup access

A production backup/recovery test requires the existing Supabase session/direct connection credentials through a secure execution path and the chosen encrypted destination. The connected SQL management tool can inspect/migrate the schema, but an automated pg_dump workflow needs its own securely configured database credential. Required secrets are now documented in [BACKUPS.md](BACKUPS.md). Do not send the database password or connection URL in chat.

The completed restore rehearsal used isolated catalog data. It does not establish a protected, retained production backup. The legacy Render sample database remains intact.

## What will be completed after these inputs arrive

- Validate each approved menu host and collection permissions; collect real dishes/prices and verify evidence, expiry and budget matching.
- Run credentialed Gemini/Places checks and verify Google Maps rendering where configured.
- Verify sender/DNS configuration, deliver a real verification/reset email, and confirm session revocation after reset.
- Exercise authorized sandbox capture, replay, refund and dispute events without moving live funds.
- Configure the selected monitoring destination and confirm a test notification to the designated recipient.
- Create an encrypted production backup, restore into an isolated target, compare records, and document recovery/retention.

A real microphone transcription check also requires a supported end-user browser and microphone permission; automated voice adapter/fallback tests already pass.
