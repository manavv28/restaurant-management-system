# BiteAI email delivery on Render Free

Render Free blocks outgoing ports 25, 465 and 587, including Gmail SMTP. A configured SMTP password does not prove delivery works. Reference: https://render.com/docs/free#other-limitations.

The prepared transport keeps the application backend on Render Free and the database on Supabase. Render sends a timestamped HMAC-authenticated HTTPS POST to the existing production Vercel project at `/api/internal/security-mail`. That server-only function sends the fixed verification/reset template through Gmail TLS SMTP and waits for completion before returning success. The sender is letsbiteai@gmail.com. No message contents, tokens or Gmail password are logged or returned to the browser.

The Gmail App Password remains stored in Render's SMTP_PASSWORD. For each send, it is transmitted over authenticated HTTPS to this private Vercel function and used in memory for Gmail login; it is not written to Vercel environment storage. This credential transfer requires explicit authorization. A separately generated signing key is stored as EMAIL_RELAY_SECRET in both production services, with no NEXT_PUBLIC prefix. The relay rejects unsigned, modified, expired, over-sized or unsupported requests and recipient header injection. It accepts only the two security templates and an operator test to the sender's own inbox. Normal account request limits remain enforced in the database. The signature window is 60 seconds; it does not provide a durable cross-instance replay ledger.

After authorization, configure Vercel production with EMAIL_RELAY_SECRET, deploy the mail function, then configure Render with:

- EMAIL_TRANSPORT=https-relay
- EMAIL_RELAY_URL=https://restaurant-management-system-qxtx.vercel.app/api/internal/security-mail
- EMAIL_RELAY_SECRET: the same production signing key

Preserve SMTP_PASSWORD, PUBLIC_APP_URL, DATABASE_URL and JWT_SECRET. Set no Gmail password in browser variables. Do not print either secret in CI or deployment logs. Do not use redirects or a third-party relay host.

The authenticated operator endpoint `/api/internal/email-test` accepts the signing key through a server-side Authorization bearer header, sends one fixed test message only to letsbiteai@gmail.com and is rate limited. Its success establishes Gmail SMTP acceptance, not inbox delivery. Confirm the inbox separately, then test an actual verification/reset link and token/session behavior.

The button now shows pending state, prevents duplicate clicks, bounds request waiting and displays delivery errors, expired-session errors and five-minute throttling feedback. No successful send is reported until Gmail acceptance.

Current activation status: automatic approval review rejected writing the new production signing secret to Vercel because explicit authorization for the secret transfer is required. The code is reviewable and tests use isolated credentials. Production activation and real delivery testing remain pending that approval. Existing production SMTP delivery from Render Free is blocked by the hosting platform.

Validation before activation: 64 PostgreSQL tests passed, all 14 Playwright tests passed (including signature validation and the button pending/error/success paths), and the Next.js production build and TypeScript checks passed. No real email was sent by these fixtures.
