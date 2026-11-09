# Optional verified payments adapter

The app never reads a user's GPay history, PINs, OTPs or passwords.

POST /payments/orders requires sign-in, payment-data consent, a real restaurant, a restaurant ID explicitly allowed in RAZORPAY_RESTAURANT_IDS and configured RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET. It creates an INR provider order associated server-side with that user and restaurant. The amount entered by the user is not verified spending.

POST /payments/webhook requires RAZORPAY_WEBHOOK_SECRET and the provider's raw-body HMAC-SHA256 x-razorpay-signature. Only payment.captured events with the known order ID, matching integer amount, INR currency and captured status create a non-simulated transaction. Row locking plus unique provider payment references prevent duplicate credit. Unknown orders, mismatched amounts and revoked consent fail for manual reconciliation. Other events are ignored. Webhook is disabled (501) without its secret.

Merchant onboarding, provider approval, restaurant settlement/routing, hosted checkout UI, refunds and dispute handling must be completed and tested before configuring real restaurant IDs. Do not turn this into a live charging flow just by entering keys. Signature, replay, amount-mismatch and consent-withdrawal tests use local signed fixtures; no live money was moved. Simulation remains visibly separate and never becomes verified spending.
