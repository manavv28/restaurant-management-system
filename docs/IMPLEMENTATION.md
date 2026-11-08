# BiteAI implementation plan
1. FastAPI relational service, authentication, ownership and clearly marked fictional sample data.
2. Structured query parsing with optional Gemini, deterministic distance/menu/ranking tools and persisted traces.
3. Favourites, history, consent, simulated spending, audited discounts and aggregate analytics.
4. Responsive Next.js search, map, account dashboard and owner portal.
5. PostgreSQL migration, automated tests, setup/deployment documentation and running-service validation.

Local SQLite and deployed PostgreSQL use identical SQLAlchemy models. Google Places supplies discovery metadata, never invented menus. Owners supply unverified menus. API integrations remain visibly optional.

Production gates: real provider credentials/testing, restaurant ownership verification, email verification/password reset, distributed rate limiting, monitoring, provider terms/retention review and payment gateway onboarding.
