# Bandra menu-source pilot — 12 November 2026

Ten existing catalog listings were checked through web search and their independently published restaurant pages. This is a small feasibility pilot, not complete neighborhood coverage. The current Google Places API key is unconfigured, so no credentialed Places/photo request or paid Google resource was used.

Results are recorded in [menu-pilot-results.json](menu-pilot-results.json), with the reproducible source manifest in [menu-pilot-bandra.json](menu-pilot-bandra.json). Initial observation: one restaurant has 91 unambiguous, explicitly marked INR dine-in dish prices; the other nine have no publishable priced menu from the checked sources. Keep those nine unpriced until evidence becomes available.

| Restaurant | Pilot result |
|---|---|
| Hakkasan Mumbai | 91 explicit prices in the official Mumbai A La Carte section. Other menus, wine and delivery prices are excluded. |
| Meraki | Listed official website returns 404. |
| Goh Jia Ting | Existing website points to Bora Bora, a different restaurant brand. No menu attached. |
| Ray's Cafe & Pizzeria | Official page links to a PDF named February 2025. Extracted text is for review; date/portion/price evidence is incomplete. |
| Elco | Official menu lists dishes without prices. |
| Jai Jawan | Bandra menu link is a coming-soon image; linked Khar/Andheri PDFs are different branches. |
| Sahibaan | Checked official site has no usable priced menu. |
| Yugo Sushi | Listed website unavailable; unrelated foreign namesakes were rejected. |
| Gracias Granny | Official page checked, without branch-specific price evidence. |
| Banana Leaf | The broad OSM area bucket includes a Juhu address; branch identity needs review. |

## Collection and import behavior

The existing catalog worker now understands explicit publisher HTML menu cards in addition to schema.org. It requires an explicitly declared INR food/dine-in section, a single dish title and a single unambiguous price. Conflicting duplicate prices, ranges, multiple variants, foreign currencies and unrelated numeric text are omitted. Evidence records contain the source URL, source hash, method, observed time and expiry. Existing price-change audits and source pause/refresh controls apply. Owner menus are not overwritten.

PUBLISHER_MENU_HOSTS extends the existing APPROVED_MENU_HOSTS list without replacing it. Only exact HTTPS hosts explicitly configured by the operator are fetched. Robots rules, response-size limits and redirect rejection remain enforced. Public publisher collection does not claim restaurant ownership or legal merchant verification.

PDF and image inspection is available through `python -m app.menu_pilot`. Native pdftotext/Tesseract work is bounded by input size, memory, CPU, output size and wall-clock time. Text extraction covers at most ten PDF pages; image-only PDFs can OCR the first page. PDF/image output remains review-only and is never automatically turned into live prices. No menu images are republished.

Google Maps is not a bulk menu feed. [Google's current Places policy](https://developers.google.com/maps/documentation/places/web-service/policies) restricts scraping, storage and derived content. Accordingly, Google is used for discovery/link lookup where available; this implementation does not harvest Maps photos into a permanent price catalog. A Google Places key alone does not resolve menu-image reuse or provide structured dishes/prices.

## Reproduce the inspection

In an isolated environment with backend dependencies and native poppler/Tesseract tools installed:

```sh
APPROVED_MENU_HOSTS=taogroup.com,img1.wsimg.com,www.elcorestaurants.com,jaijawanfoods.com,www.sahibaan.com,graciasgranny.com \
PYTHONPATH=backend python -m app.menu_pilot \
  --manifest docs/menu-pilot-bandra.json --output /tmp/menu-pilot-results.json
```

The CLI writes a review report only and does not modify the database. Native inspection runs serially for the Render Free memory budget. The existing supervised catalog worker performs publication only for the explicitly approved HTML source. No schema migration is needed for this feature.

## Activation checkpoint

The pilot source and importer are prepared. Live Hakkasan source registration, successful worker execution and a public budget-search check must be recorded after deployment before reporting prices as available in production. Render Free and Supabase remain the target; no paid resource or owner onboarding is required for this pilot.
