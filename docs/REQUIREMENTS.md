# PROJECT: BiteAI — AI-Native Restaurant Discovery & Personalised Offers Platform

Act as a Senior Full-Stack Engineer, AI Engineer, Product Architect, UI/UX Designer and Agentic AI Developer.

Your task is to design and build a complete, professional, production-minded MVP called **BiteAI**.

Do not build just a chatbot or a static frontend. Build a functional end-to-end application with a real database, backend APIs, AI agents, restaurant discovery, menu search, location-based filtering, and a personalised discount system.

The application must be built with a strong emphasis on Agentic AI. Any repetitive data collection, enrichment, classification, search, and business workflow that can be automated should be handled by AI agents.

## 1. PRODUCT OBJECTIVE

BiteAI is an AI-powered restaurant discovery platform focused entirely on Mumbai, India.

Users should be able to search for food using natural language through voice or text.

Example user query:

"I feel like eating Chinese. Find me Hakka noodles under ₹300 within a 2 km radius."

The system should:
- Understand the user's food preference.
- Extract cuisine, dish, budget and distance.
- Identify the user's location.
- Search restaurants in Mumbai.
- Search their available menus and prices.
- Compare results against the user's requirements.
- Show matching restaurants with distance, pricing, address, ratings and contact information where available.
- Recommend the best matches.
- Show external ordering options when available.
- Offer personalised discounts based on user activity and spending.

The application must feel like a real consumer product, not a college project.

## 2. TECHNOLOGY STACK

Use the following stack unless a genuine technical limitation requires an alternative:

Frontend:
- Next.js
- TypeScript
- Tailwind CSS
- Modern component architecture
- Responsive mobile-first UI

Backend:
- Python
- FastAPI
- REST APIs

Database:
- Supabase
- PostgreSQL
- PostGIS for geospatial queries where available

AI:
- Gemini API or another suitable LLM
- Tool-calling/function-calling architecture
- Agent orchestration with structured outputs

Maps:
- Google Maps Platform
- Google Places API

Voice:
- Browser Speech Recognition API where supported
- Text search fallback

Automation:
- Background jobs and scheduled workflows
- n8n if useful

Deployment:
- Vercel for frontend
- Render or another suitable backend host
- Supabase for database

Use environment variables for every API key and secret.

## 3. USER INTERFACE AND EXPERIENCE

Create a premium, modern and polished interface.

Design direction:
- Clean and minimal.
- Premium food-tech aesthetic.
- Strong typography.
- Smooth transitions.
- Excellent mobile responsiveness.
- Beautiful restaurant cards.
- Interactive maps.
- Clear pricing and discount indicators.

Main landing page:

The first screen should contain:

1. BiteAI branding.
2. Location selector.
3. Prominent voice search button.
4. Natural language search bar.
5. Suggested food categories.
6. Nearby restaurants.
7. Popular dishes.
8. Personalised recommendations.
9. Available discounts.

The search experience should be the main focus.

Example search interface:

"Tell us what you're craving..."

Include:
- Microphone button.
- Text input.
- Search button.
- Current location.
- Budget selector.
- Distance selector.

## 4. AI SEARCH AGENT

Build an actual AI agent that understands natural-language food queries.

Example:

"I want spicy Chinese food, preferably Hakka noodles, under ₹300, within 2 km."

The agent should extract structured information:

{
  "cuisine": "Chinese",
  "dish": "Hakka noodles",
  "max_budget": 300,
  "radius_km": 2,
  "location": "user_location"
}

The agent should then:

1. Understand the query.
2. Resolve location.
3. Identify search parameters.
4. Query the central restaurant database.
5. Search external permitted data sources when necessary.
6. Match dishes and prices.
7. Filter by distance and budget.
8. Rank the results.
9. Explain why each restaurant matches.
10. Return structured results to the frontend.

Use deterministic backend filtering for prices and distance. Do not rely on the LLM to calculate these values.

Handle missing information by asking the user a relevant follow-up question.

## 5. RESTAURANT DATA LAKE — MUMBAI

Create a central restaurant data lake containing restaurant information across Mumbai.

Store:

Restaurant:
- Restaurant name
- Address
- Latitude
- Longitude
- PIN code
- Area
- Cuisine
- Phone number, when publicly available
- Website
- Rating
- Price range
- Opening hours
- Source
- Last updated timestamp

Menu:
- Dish name
- Restaurant ID
- Category
- Cuisine
- Price
- Description
- Availability, if known
- Source
- Last verified timestamp

Create proper relational database tables and indexes.

Important:
- Use Google Places API and permitted public sources.
- Respect Zomato and Swiggy terms of service.
- Do not bypass authentication or scrape restricted platforms.
- Where official APIs or permitted integrations are unavailable, provide external links rather than pretending to have live access.
- Never invent restaurant menus, prices, phone numbers or ratings.
- Clearly distinguish verified information from unverified information.
- Include source attribution and data freshness.

Build an ingestion pipeline that can collect, clean, deduplicate, classify and update restaurant information.

The initial dataset should cover multiple Mumbai areas and support expansion.

Do not falsely claim complete Mumbai-wide coverage when only a subset is available.

## 6. AGENTIC AI ARCHITECTURE

Create specialised agents with clear responsibilities.

A. Restaurant Discovery Agent
- Finds restaurants.
- Retrieves restaurant information.
- Identifies available menu sources.

B. Menu Intelligence Agent
- Extracts dishes and prices.
- Categorises cuisines.
- Matches user cravings to menu items.
- Identifies price changes.

C. Location Agent
- Handles coordinates.
- Calculates restaurant distances.
- Finds restaurants within the requested radius.

D. Recommendation Agent
- Ranks restaurants.
- Considers price, distance, cuisine, ratings and user preferences.
- Explains recommendations.

E. Discount Agent
- Identifies eligible users.
- Evaluates restaurant discount rules.
- Calculates personalised offers.
- Tracks discount redemption.

F. Data Lake Agent
- Cleans collected data.
- Removes duplicates.
- Updates restaurant records.
- Tracks source and freshness.

IMPORTANT:
These must be functional workflows, not just different agent names in the UI.

Implement clear tool interfaces, structured outputs, error handling, logging and agent execution traces.

Avoid unnecessary multi-agent complexity. Use deterministic tools for tasks such as database queries, distance calculation and financial calculations.

## 7. PERSONALIZED RESTAURANT DISCOUNT SYSTEM

Build a working discount engine.

Restaurants should be able to:
- Create discount campaigns.
- Define eligibility rules.
- Offer discounts based on user query count.
- Offer discounts based on spending.
- Define minimum order value.
- Define maximum discount.
- Set campaign validity.
- Set redemption limits.

Example:

A restaurant can offer:
- 5% discount after 5 food searches.
- 10% discount after ₹2,000 verified spending.
- Special offers for repeat customers.

Users should have:
- Personal offer dashboard.
- Available discounts.
- Eligibility status.
- Redemption history.
- Spending history.

Implement an auditable discount calculation system.

Do not treat search queries as proof of purchases.

## 8. UPI / GPAY INTEGRATION

Build a consent-based payment and transaction verification architecture.

Users must explicitly opt in.

Important security requirements:
- Never request or store UPI PINs.
- Never collect Google Pay credentials.
- Never store payment passwords or OTPs.
- Do not claim access to a user's complete GPay history.
- Use authorised payment gateway integrations, verified transaction webhooks, or supported consent-based financial data integrations.
- Store only necessary transaction references and verified spending summaries.
- Allow users to withdraw consent.

For the MVP, build the integration-ready architecture and a safe simulated transaction verification flow if live provider access is unavailable.

## 9. RESTAURANT PORTAL

Create a restaurant onboarding and management portal.

Restaurants should be able to:
- Register.
- Manage restaurant details.
- Add or update menus.
- Update dish prices.
- Add phone numbers and websites.
- Create discount campaigns.
- View search activity.
- View customer engagement analytics.
- Track discount redemptions.

Create appropriate role-based permissions.

## 10. USER DASHBOARD

Users should be able to:
- Register and log in.
- Manage their profile.
- Save favourite restaurants.
- Save favourite dishes.
- View search history.
- View personalised recommendations.
- View eligible discounts.
- Track verified spending.
- Manage location permissions.
- Manage payment-data consent.

## 11. CENTRAL DATA LAKE AND ANALYTICS

Maintain a central repository for:

- Restaurant information.
- Menu information.
- Search queries.
- Search results.
- User preferences.
- Restaurant interactions.
- Discount campaigns.
- Verified transaction summaries.
- Agent execution logs.
- Data source and freshness information.

Build analytics dashboards showing:
- Most searched cuisines.
- Most searched dishes.
- Popular restaurant areas.
- Average user budget.
- Most requested dishes.
- Search-to-restaurant-click conversion.
- Discount campaign performance.

Implement privacy controls, access restrictions and retention policies. Do not expose individual users' personal search history to restaurants without appropriate consent.

## 12. SEARCH RESULTS UI

Each restaurant card should show:

- Restaurant name.
- Restaurant image, when available.
- Rating and review count, when available.
- Distance.
- Area and address.
- Matching dish.
- Verified dish price.
- Budget match.
- Phone number, when publicly available.
- Directions.
- Menu link.
- External ordering link, where available.
- Eligible discounts.

Clearly label estimated, unavailable and unverified information.

Provide both map view and list view.

## 13. TESTING AND QUALITY

Implement:
- Backend unit tests.
- API integration tests.
- Database validation.
- Authentication tests.
- Role and permission tests.
- AI query parsing tests.
- Distance calculation tests.
- Discount calculation tests.
- Error handling.
- Responsive UI testing.

Test the complete user journey:

1. User opens BiteAI.
2. User grants location access.
3. User searches by voice or text.
4. AI extracts the query.
5. Backend searches the database.
6. Matching restaurants are returned.
7. User opens a restaurant.
8. User views the menu.
9. User checks eligible discounts.

## 14. DEVELOPMENT RULES

Follow these instructions throughout development:

1. First inspect the existing project and its files.
2. Do not overwrite working code unnecessarily.
3. Create a clear architecture and folder structure.
4. Create a detailed implementation plan.
5. Implement the application in working stages.
6. Do not stop after creating a plan or design.
7. Write actual functional code.
8. Install necessary dependencies.
9. Run the application and resolve build errors.
10. Test APIs and important user journeys.
11. Create seed data for demonstration purposes.
12. Clearly label seed data as sample data.
13. Add a complete .env.example file.
14. Add setup and deployment instructions in README.md.
15. Never hardcode API keys.
16. Never fake successful external API calls.
17. Never invent data to make the interface appear populated.
18. Keep the architecture modular and maintainable.

When an API key or external service is unavailable, build the integration interface, document the missing configuration and provide a working fallback wherever possible.

## 15. FINAL DELIVERABLE

The final product must include:

- Working frontend.
- Working backend.
- Supabase database schema and migrations.
- AI search agent.
- Restaurant data ingestion pipeline.
- Central data lake.
- Restaurant portal.
- User dashboard.
- Voice and text search.
- Interactive map.
- Personalised discount engine.
- Payment integration architecture.
- Analytics.
- Automated tests.
- README and deployment guide.

The goal is to create a professional, demonstrable, AI-native restaurant discovery product focused on Mumbai.

Think like a product engineer building a real startup, not someone completing a basic academic assignment.

Start by inspecting the repository, then create the implementation plan and immediately begin building the working MVP.

Do not ask me to manually implement code that you can implement yourself. Explain any actions that require my API keys, permissions or explicit approval.
