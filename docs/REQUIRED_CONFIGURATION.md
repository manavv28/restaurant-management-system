# Inputs needed to finish BiteAI's live integrations

The application is deployed at https://restaurant-management-system-qxtx.vercel.app. Keep the existing Render Free backend and Supabase database. This guide lists the configuration still needed; it does not claim these services are configured or verified.

## Information you can provide in chat

1. **Menu sources:** two or three restaurant menu URLs/domains you own or have permission to collect from. Alternatively, identify restaurant-authorized menu exports. Include which restaurant each source belongs to. This unlocks real dishes/prices and the complete budget-match journey; the 378 current OSM records contain no inferred menu prices.
2. **Email sender:** a verified sender address/domain and the email provider you want to use. If DNS verification is required, identify the domain and where its DNS is managed.
3. **Alert recipient:** the email address or existing alert destination that should receive incident notifications. Identify an existing monitoring account if you already have one.
4. **Backup destination:** choose encrypted GitHub artifacts retained seven days as a free starting option, or name an existing private storage destination and desired retention. Confirm the destination before its backup workflow is configured. Keep the decryption key separately from backup files.
5. **Payments:** identify the onboarded restaurant/merchant and whether you have a Razorpay test account. Complete legal/KYC and settlement approval directly with the payment provider before any live charging.

## Secrets to enter through secure settings

Do not paste secret values in chat, commit them, or upload a live .env file. Existing Render/Vercel connections can manage deployment settings, but they do not supply Gemini, Google, SMTP, merchant or database-backup credentials automatically.

### Render → biteai-demo → Environment

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

A production backup/recovery test requires the existing Supabase session/direct connection credentials through a secure execution path and the chosen encrypted destination. The connected SQL management tool can inspect/migrate the schema, but an automated pg_dump workflow needs its own securely configured database credential. Exact workflow secret names will be documented when the destination is chosen. Do not send the database password or connection URL in chat.

The completed restore rehearsal used isolated catalog data. It does not establish a protected, retained production backup. The legacy Render sample database remains intact.

## What will be completed after these inputs arrive

- Validate each approved menu host and collection permissions; collect real dishes/prices and verify evidence, expiry and budget matching.
- Run credentialed Gemini/Places checks and verify Google Maps rendering where configured.
- Verify sender/DNS configuration, deliver a real verification/reset email, and confirm session revocation after reset.
- Exercise authorized sandbox capture, replay, refund and dispute events without moving live funds.
- Configure the selected monitoring destination and confirm a test notification to the designated recipient.
- Create an encrypted production backup, restore into an isolated target, compare records, and document recovery/retention.

A real microphone transcription check also requires a supported end-user browser and microphone permission; automated voice adapter/fallback tests already pass.
