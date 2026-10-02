# Shopify App Store listing requirements used for Expedo

Read on **2026-10-02** from shopify.dev. Shopify changes these pages; check them again before submitting.

Sources:

- **[REQ]** App Store requirements: https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements (section 4 "App Store Listing", plus sections 1–3 for privacy and scopes)
- **[BP]** Best practices for apps in the Shopify App Store: https://shopify.dev/docs/apps/launch/shopify-app-store/best-practices (section "App listing": A. branding, B. listing content, E. app discovery, F. install eligibility, G. app review preparation)
- **[CL]** Changelog, "Clearer standards for app listing images" (12 March 2026, in force from 26 March 2026): https://shopify.dev/changelog/clearer-standards-for-app-listing-images
- **[PCD]** Work with protected customer data: https://shopify.dev/docs/apps/launch/protected-customer-data
- **[SUB]** Submit your app for review: https://shopify.dev/docs/apps/launch/app-store-review/submit-app-for-review (app icon in the app configuration, emergency contact, at least one listing)

## Limits and formats

| Field / asset | Requirement | Source | How the kit meets it |
|---|---|---|---|
| App name | Max **30 characters**. Leads with your own brand; unique; not a Shopify or third-party name; same as or "similar" to the name in the TOML / Dev Dashboard | BP A.1, REQ 4.1.1, 4.1.2 | `Expedo` (6). TOML name is `Expedo`. Alternatives in `LISTING-COPY.en.md` keep "Expedo" first. |
| App icon | **1200 × 1200 px, JPEG or PNG**, square with padding (Shopify rounds the corners), bold colours, simple pattern. No text, no screenshots, no Shopify trademarks, no copied logos | BP A.2, SUB | `icon/expedo-icon-1200.png`: full-bleed square (no own rounding), parcel mark with ~23 % padding, no text. |
| App card subtitle | Concise phrase of what the app does and its value. No keywords added for search, no merchant data without consent, no data or statistics. **62 characters**: limit enforced by the Partner Dashboard form; shopify.dev does not print the number (third-party guides agree on 62) | REQ 4.4.1, BP E | EN 57, RO 60. Verify the counter in the form. |
| App introduction | Max **100 characters**. Benefit for the merchant, no keyword stuffing, no data claims, full sentences | BP B.4 | EN 96, RO 95. |
| App details | Max **500 characters**. Functional description, what makes it different; no excessive marketing language, keyword stuffing, outcome guarantees; no support info, links or testimonials | BP B.5, REQ 4.4.2 | EN 488, RO 484. |
| Feature list | Max **80 characters per feature**; functionality, not technical mechanics; no keyword stuffing. Number of features not stated | BP B.6 | 9 features, all ≤ 80. |
| Feature media | Video 2–3 min, promotional, screencast ≤ 25 % of it, **or a static image 1600 × 900 px (16:9)**: one focal point, solid background, contrast 4.5:1 recommended, alt text, no Shopify logos, don't repeat the app card subtitle | BP B.1 | Static image `feature/feature-en.png` (and `-ro`). Solid cobalt `#1f4bd8`; white text on it is ~6.9:1. Title differs from the subtitle. A promotional video is optional; the review screencast is *not* suitable as feature video (it is instructional). |
| Desktop screenshots | **1600 × 900 px (16:9), 3–6**, at least one of the app UI; crop out browser chrome and sensitive information; alt text; no PII, pricing, reviews or outcome guarantees | BP B.3 | 6 screenshots, real UI, no browser chrome, fictional demo customers. |
| Mobile screenshots | Include if the app is mobile-responsive or works with POS. Size not stated on the current pages; Shopify's earlier guidance (still returned by its search) gives **900 × 1600 px (9:16)**, not duplicates of the desktop set | BP B.3 | The UI is responsive (breakpoint 900 px), so 3 mobile screenshots at 900 × 1600 showing different views. |
| Images in general | Primarily the app's real UI and features; no desktop backgrounds or browser windows; no images that only show the logo; every image unique, different features/views/states | REQ 4.4.4, 4.4.5, CL | Each image shows a different screen or state. |
| Pricing | Only in the Pricing section; never in images or the icon; complete (trial, charges) | REQ 4.2.1–4.2.3, BP | No prices anywhere in the images or copy. Plans left as DRAFT for the owner (LISTING.md). |
| Statistics / claims | No statistics or data (verifiable or not) in listing content, overview or introduction, nor in images; avoid "the first", "the best", "the only"; no guarantees | REQ 4.3.3, 4.3.4 | No numbers, superlatives or guarantees in the copy or captions. |
| Reviews / testimonials | Not in the listing, not in images | REQ 4.3.6, 4.3.7 | None. |
| Shopify brand | No Shopify trademarks in icon, banner or screenshots except to state compatibility per the brand guidelines | REQ 4.4.3, BP B.1 | No Shopify logo anywhere; the word "Shopify" appears only inside the app's own UI labels. Captions avoid it. |
| Other apps/services | Don't reference your other apps and services | REQ 4.4 | None referenced; no competitor named. |
| Languages | List only languages in which merchants can use the app UI | REQ 4.3.2 | Expedo's UI is Romanian only → Languages: **Romanian**. The English listing is allowed; it says the interface is Romanian. |
| Geography | State geographic requirements needed for the app to work | REQ 4.3.8, BP F | Details say "For stores shipping in Romania"; set install eligibility to Romania (see LISTING.md). |
| Search terms | Up to **5**, complete words, one idea per term | BP E | 5 terms per language. |
| Categories / tags | Accurate, reflect primary function; up to 25 structured features per category | REQ 4.3.5, BP E | Suggestion in LISTING.md. |
| Integrations | Up to **6**; not Shopify itself, not other carts or Shopify apps unless directly integrated | BP B.7 | 8 direct integrations exist; recommended 6 in LISTING.md. |
| Translated listings | Automatic translation covers subtitle, introduction, details, features, pricing details, search terms, image alt text (pt-BR, da, nl, fr, de, zh-CN, es, sv); custom translations can be added in the Partner Dashboard | BP "Translated listings" | Romanian copy ready in `LISTING-COPY.ro.md` for a custom translation, if Romanian is offered. |
| Privacy policy | Required link; link dedicated pages, not cloud documents | BP E, BP "Data and user privacy" | App will serve `/privacy` (EN) and `/confidentialitate` (RO) once deployed. |
| Demo store URL | Link to a development store page that best shows the app, with context | BP B.2 | Expedo works in the admin only (nothing on the storefront): leave empty or link a dev store; see LISTING.md. |

## Review submission

| Requirement | Source | How |
|---|---|---|
| Screencast showing onboarding and features as described in the listing, **clear step-by-step setup of the core features**, in English or with English subtitles | REQ 4.5.3, BP G | `review/expedo-review-screencast.mp4` (2:36, 1920×1080, English captions burned in, `.srt` alongside). |
| Test credentials valid and granting full access; keep them up to date | REQ 4.5.4, 4.5.5 | Expedo needs no login of its own inside Shopify; third-party accounts are replaced by **Test mode**. If the owner hosts a standalone demo with `ADMIN_PASSWORD`, put that password in the testing instructions. See REVIEW-INSTRUCTIONS.md. |
| "Demonstrate the expected outcome for each test case" | BP G | Each step in REVIEW-INSTRUCTIONS.md has an "Expected" line. |
| Emergency developer contact in the Partner Dashboard | REQ 4.5.6, SUB | Owner checklist. |
| Regular app, not a Sales Channel | REQ 4.5.1, 4.5.2 | `shopify.app.toml` has no sales-channel config. |
| Only necessary scopes | REQ 3.2 | `read_orders, write_orders, read/write_merchant_managed_fulfillment_orders` (no `read_all_orders`, no `read_customers`). |
| App icon also set in the app configuration (1200 × 1200, JPEG/PNG) | SUB | Upload the same `expedo-icon-1200.png` in the Dev Dashboard app settings. |

## Protected customer data

| Level | Data | What it means for a public app | Source |
|---|---|---|---|
| 1 | Customer data without name, address, phone, email | Request access in Partner Dashboard → API access requests; meet level 1 requirements | PCD |
| **2** | **Name, address, phone or email** | Request access to protected customer data **and** each field; meet level 1 and 2 requirements; may be selected for a data protection review | PCD |

Expedo reads, from each order, the shipping/billing **name, address, phone and email** (AWB recipient, invoice client; see `src/shopify/queries.js`) → **level 2**, fields: Name, Address, Phone, Email. Reasons to give in the request are in LISTING.md. Level 1 requirements include: process only the minimum data, tell merchants what is processed and why (privacy policy), limit processing to that purpose, respect consent and opt-out decisions, don't keep personal data longer than necessary, encrypt data at rest and in transit. Level 2 adds: encrypt backups, separate test and production data, data-loss prevention, limited staff access, strong passwords, access logs, an incident response policy. Development stores can use the data before approval once the fields are selected and the details completed.
