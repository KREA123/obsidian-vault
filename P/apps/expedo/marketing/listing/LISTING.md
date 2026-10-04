# Expedo: Shopify App Store listing kit (English)

Everything needed to fill in the Partner Dashboard listing for **Expedo** (publisher ARTEMIS DIGITAL SRL, support office@krea.ro). There is one listing, in **English**. Rules and sources: [REQUIREMENTS.md](REQUIREMENTS.md). Texts to paste, with character counts: [LISTING-COPY.md](LISTING-COPY.md). Reviewer material: [REVIEW-INSTRUCTIONS.md](REVIEW-INSTRUCTIONS.md) and `review/`. The v1 Romanian copy and images (taken from the earlier Romanian-only UI) are kept in `ro-archive/` for reference only; nothing there is part of the listing.

## Rebuild

```bash
node P/apps/expedo/marketing/listing/build.mjs                # everything (about 3 min)
node P/apps/expedo/marketing/listing/build.mjs copy           # only LISTING-COPY.md (+ limit checks)
node P/apps/expedo/marketing/listing/build.mjs icon screens   # icon, screenshots, feature image
node P/apps/expedo/marketing/listing/build.mjs video          # review screencast
```

Words live in `copy.mjs`. The build fails if a field is over its limit, a caption overflows its image or contains a price, or a capture falls outside the browser window. Layout and capture are in `build.mjs`, the screencast in `screencast.mjs`. The build runs the frozen app copy `/tmp/claude-0/expedo-snap2/P/apps/expedo` (English UI) in demo mode (`DEMO=1`) on a throwaway database (`/tmp/claude-0/listing-demo.db`, port 3302), drives the real UI with Playwright (Chromium; deviceScaleFactor 2 for screenshots, 1.5 for the 1080p video) and never touches the app source. Override with `EXPEDO_APP_DIR`, `PORT`, `DB_FILE`, `CHROMIUM_PATH`, `PLAYWRIGHT_MODULE`. Needs `ffmpeg`, `pdftoppm`, Python 3 with Pillow (lossless PNG optimisation). Fonts (Inter, JetBrains Mono, OFL) and FAN Courier's public Ilfov locality list are cached in `assets/`.

**About the demo state in the images.** The demo store always runs in Test mode, so AWBs and invoices are numbered `TEST…` and orders carry a yellow "TEST" pill: real app states, left as they are. The yellow Test-mode banner is hidden in the screenshots except screenshot 4 (the Test-mode screen), because a live store doesn't show it. Two things are set up in the throwaway database with the app's own code: (1) order #1116 carries the customer typo "Volutari" and FAN Courier's rejection "Did you mean: Voluntari, Pipera (Voluntari), Luparia?", produced by the app's `localityError()` on FAN Courier's public locality list (the demo has no courier account, so the real courier call can't happen); (2) the demo's test AWBs are aged a few minutes, as the app's own demo seeding does, so some parcels are already delivered. The refused-parcel warning on #1111 is the app's own demo data. Customer names, addresses and phones are fictional.

## Where each asset goes in the Partner Dashboard

Partner Dashboard → Apps → Expedo → Distribution → Shopify App Store → **Manage listing** (English).

<!-- assets:start -->
| File | Size | Purpose | Form field |
|---|---|---|---|
| `icon/expedo-icon-1200.png` | 1200×1200, 40 KB | App icon, square (Shopify rounds the corners), no text | **App icon** in the listing and in the app configuration (Dev Dashboard) |
| `icon/expedo-icon-512.png` | 512×512, 16 KB | Smaller export of the icon | Not uploaded; website, e-mail, docs |
| `icon/expedo-icon-256.png` | 256×256, 8 KB | Smaller export of the icon | Not uploaded; website, e-mail, docs |
| `icon/expedo-icon-128.png` | 128×128, 4 KB | Smaller export of the icon | Not uploaded; website, e-mail, docs |
| `icon/expedo-icon-64.png` | 64×64, 2 KB | Smaller export of the icon | Not uploaded; website, e-mail, docs |
| `icon/expedo-icon-rounded-512.png` | 512×512, 21 KB | Rounded-corner variant | Not uploaded to Shopify (it rounds the square itself); website, favicon |
| `icon/expedo-icon-rounded-64.png` | 64×64, 2 KB | Rounded-corner variant | Not uploaded to Shopify (it rounds the square itself); website, favicon |
| `icon/expedo-icon.svg` | 1 KB | Vector master of the icon | Source |
| `icon/expedo-icon-rounded.svg` | 1 KB | Vector master, rounded variant | Source |
| `icon/icon-preview.png` | 900×300, 24 KB | Icon at 160/96/64/32 px on light and dark | Check only |
| `feature/feature.png` | 1600×900, 97 KB | Feature image: From order to AWB, invoice and collected cash | **Feature media** (static image) |
| `screenshots/01-dashboard.png` | 1600×900, 207 KB | Screenshot 1: See what needs doing today | **Desktop screenshots**, position 1 |
| `screenshots/02-address-check.png` | 1600×900, 139 KB | Screenshot 2: Fix the address before the courier rejects it | **Desktop screenshots**, position 2 |
| `screenshots/03-bulk-awb-invoice.png` | 1600×900, 259 KB | Screenshot 3: AWB and invoice for many orders at once | **Desktop screenshots**, position 3 |
| `screenshots/04-rules-test-mode.png` | 1600×900, 202 KB | Screenshot 4: Your rules, tried safely in test mode | **Desktop screenshots**, position 4 |
| `screenshots/05-tracking-cod.png` | 1600×900, 158 KB | Screenshot 5: Track every parcel until the cash is in | **Desktop screenshots**, position 5 |
| `screenshots/06-couriers-invoicing.png` | 1600×900, 139 KB | Screenshot 6: Connect your couriers and invoicing | **Desktop screenshots**, position 6 |
| `screenshots/mobile/m1-dashboard.png` | 900×1600, 187 KB | Mobile screenshot 1: Today's orders, on your phone too | **Mobile screenshots**, position 1 |
| `screenshots/mobile/m2-refused.png` | 900×1600, 168 KB | Mobile screenshot 2: Know who refused parcels before | **Mobile screenshots**, position 2 |
| `screenshots/mobile/m3-delivered.png` | 900×1600, 186 KB | Mobile screenshot 3: Delivered and cash collected, at a glance | **Mobile screenshots**, position 3 |
| `screenshots/labels-sample.pdf` | 3 KB | The labels PDF rendered in screenshot 3 (test labels) | Reference only |
| `review/expedo-review-screencast.mp4` | 1920×1080, 2:40, 5.1 MB | Screencast for review: real walkthrough of the demo UI, English captions burned in, H.264 CRF 23 | **Testing instructions → screencast** (upload, or unlisted video link) |
| `review/expedo-review-screencast.en.srt` | 4 KB | The screencast captions as subtitles | Optional: subtitles if uploaded to YouTube/Vimeo |
| `review/screencast-chapters.json` | 4 KB | Caption timestamps | Reference for the reviewer notes |
<!-- assets:end -->

## Listing fields that are not files

| Field | Value | Notes |
|---|---|---|
| App name | `Expedo` | Must stay similar to `name` in `shopify.app.toml` (req. 4.1.1). Short names don't truncate in the admin nav. |
| App card subtitle, introduction, details, features, search terms, pricing text | `LISTING-COPY.md` | Character counts next to each field. |
| Screenshot / feature image alt text | `LISTING-COPY.md` | Required by Shopify for every image. |
| Feature media | Static image `feature/feature.png` | No promotional video yet. If one is made later: 2–3 min, promotional, screencast parts ≤ 25 %. Don't use the review screencast here. |
| Demo store URL | Leave empty, or a development store | Expedo has nothing on the storefront; a storefront link wouldn't show the app. |
| Integrations (max 6) | **Cargus, Sameday, FAN Courier, SmartBill, Oblio, FGO** (recommended) | All eight are direct integrations: Cargus, Sameday, FAN Courier, GLS, DPD, SmartBill, FGO, Oblio. Names only, no logos. Swap in GLS / DPD if your merchants use them more. |
| Languages | **English, Romanian** | The app UI is usable in both (req. 4.3.2): English by default, Romanian in Settings → General → Language, and the Shopify admin language when embedded. |
| Categories | Primary: **Orders and shipping › Shipping solutions › Shipping**. Secondary, if offered: **Orders and shipping › Orders › Invoices and receipts** (or **Order tracking**) | Pick the structured features that are true (labels, carriers, tracking, invoices). Taxonomy read from apps.shopify.com on 2026-10-02. |
| Install eligibility | Geography: **Romania** (store country / ships to Romania); currency RON | Req. 4.3.8: the couriers and invoicing apps only work for Romania. Online Store channel **not** required. |
| Privacy policy URL | `https://<app-host>/privacy` | Required. Served by the app (Romanian version at `/confidentialitate`). Terms at `/terms`. |
| Support | E-mail `office@krea.ro`; optional FAQ / docs page (dedicated pages, not cloud documents) | — |
| Testing instructions | Block "Paste into Testing instructions" in REVIEW-INSTRUCTIONS.md | Attach or link the full file and the screencast. |
| Screencast | `review/expedo-review-screencast.mp4` | Upload, or an unlisted YouTube/Vimeo link if the form asks for a URL. |

## Pricing

Matches the app (`P/apps/expedo/PRICING.md`, `src/core/plans.js` in the live tree). **Shopify App Pricing** (formerly "managed pricing"), billing method **Recurring charge**, prices in **USD every 30 days**. **No free plan: both plans have a 5-day free trial.** Set up the plans as described in PRICING.md (display names exactly Pro / Pro Max; "Free for partners and developers" on). Display names and top features for the listing are in `LISTING-COPY.md`.

| Plan | Price | Trial | Orders | Top features (English, as in PRICING.md) |
|---|---|---|---|---|
| Pro | $15 | 5 days | up to 1,000 every 30 days | Up to 1,000 orders every 30 days · All couriers and invoicing apps · Address & phone check · Test mode · Bulk processing and rules · Tracking and COD reconciliation |
| Pro Max | $30 | 5 days | unlimited | Unlimited orders · Everything in Pro · Automatic processing of new orders · Customer refusal history · COD export (CSV) · Multiple stores · Priority support |

"Orders" means orders that get a live AWB in the billing period; test-mode AWBs never count. Without an active plan (trial canceled, subscription expired) the app keeps test mode, tracking and existing documents working but creates no live AWBs or invoices. shopify.dev states no character limit for plan display names or top features; each top feature here is under 80 characters (the listing's own feature limit). Prices appear only in the Pricing section, never in images (req. 4.2). No additional charges. Shopify recommends a 14-day trial (REQUIREMENTS.md); 5 days is the owner's choice.

## Protected customer data request (level 2)

Partner Dashboard → Apps → Expedo → API access requests → Protected customer data → Request access. Select **Name, Address, Phone, Email**. Reasons to paste:

- **Name and address:** printed on the courier AWB (shipping label) and on the invoice the merchant issues for the order.
- **Phone:** required by Romanian couriers to deliver; the courier calls the recipient. Also used, with the e-mail, to recognise a returning customer for the refused-parcel warning.
- **Email:** passed to the merchant's invoicing app as the client's e-mail on the invoice (the invoicing app e-mails the invoice only if the merchant turns that on). Not used for marketing.
- Data comes from orders only (no `read_customers`), is used only to ship, invoice and warn about past refusals within the same store, and is deleted on `customers/redact` and `shop/redact` and after the retention period set in Settings → Customer data.

Then complete the data protection details (level 1 and 2 requirements, see REQUIREMENTS.md).

## Owner checklist

- [ ] Deploy the app on its final host; set `application_url` / `redirect_urls` / `client_id` in `shopify.app.toml`; `shopify app deploy`.
- [ ] Check that `https://<app-host>/privacy` is live; put the URL in the listing.
- [ ] Upload `icon/expedo-icon-1200.png` in the app configuration (Dev Dashboard) and in the listing.
- [ ] Paste the copy from `LISTING-COPY.md`. Check the subtitle counter in the form (62).
- [ ] Upload `feature/feature.png`, the six `screenshots/*.png` in order 01–06 and the three `screenshots/mobile/*.png`; paste each alt text.
- [ ] Set up the two plans (Pro $15, Pro Max $30, 5-day free trial each) in Shopify App Pricing exactly as in PRICING.md; unpublish any old Free / Starter / Growth / Plus plans; check the listing shows the 5-day trial on both.
- [ ] Pick the 6 integrations, categories and structured features; Languages = English, Romanian; install eligibility = Romania.
- [ ] Request protected customer data (level 2: name, address, phone, email) with the reasons above; complete data protection details.
- [ ] Add the emergency developer contact (Partner account settings).
- [ ] Fill the OWNER parts of REVIEW-INSTRUCTIONS.md (FAN Courier public test account, FGO test environment account, optional hosted demo URL + password) or delete them.
- [ ] Screencast: step 1 (install and plan choice) is a title card because there was no deployed app or development store here. Shopify asks the screencast to show onboarding, so after deploying, consider recording the real install and plan selection on a development store (about 20 s) and placing it after the intro card. The screencast was recorded from an app copy without the plan banner and Settings → Plan screen.
- [ ] Re-read the REQUIREMENTS.md sources right before submitting; Shopify updates them.
