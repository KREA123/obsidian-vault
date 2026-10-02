# Expedo: Shopify App Store listing kit

Everything needed to fill in the Partner Dashboard app listing for **Expedo** (publisher ARTEMIS DIGITAL SRL, support office@krea.ro). The rules each asset follows, with the shopify.dev links, are in [REQUIREMENTS.md](REQUIREMENTS.md). The texts to paste are in [LISTING-COPY.en.md](LISTING-COPY.en.md) (primary listing) and [LISTING-COPY.ro.md](LISTING-COPY.ro.md). Reviewer material: [REVIEW-INSTRUCTIONS.md](REVIEW-INSTRUCTIONS.md) and `review/`.

## Rebuild

```bash
node P/apps/expedo/marketing/listing/build.mjs                # everything (≈ 3 min)
node P/apps/expedo/marketing/listing/build.mjs copy           # only LISTING-COPY.*.md (+ limit checks)
node P/apps/expedo/marketing/listing/build.mjs icon screens   # icon, screenshots, feature image
node P/apps/expedo/marketing/listing/build.mjs video          # review screencast
```

Words live in `copy.mjs` (the build fails if a field is over its limit or a caption overflows its image); layout and capture in `build.mjs`; the screencast script in `screencast.mjs`. The build starts the app in demo mode (`DEMO=1`, 19 Romanian demo orders) on a throwaway database, drives the real UI with Playwright (Chromium, deviceScaleFactor 2 for screenshots, 1.5 for the 1080p video) and never touches the app source. Defaults: the frozen app copy `/tmp/claude-0/expedo-snap/P/apps/expedo` when present (else `../..`), port 3302, DB `/tmp/claude-0/listing-demo.db`, Chromium `/opt/pw-browsers/chromium-1194`; override with `EXPEDO_APP_DIR`, `PORT`, `DB_FILE`, `CHROMIUM_PATH`, `PLAYWRIGHT_MODULE`. Needs `ffmpeg`, `pdftoppm`, Python 3 with Pillow (lossless PNG optimisation). Fonts (Inter, JetBrains Mono, OFL) and FAN Courier's public Ilfov locality list are cached in `assets/`.

**About the demo state in the images.** The demo store always runs in Test mode, so AWBs and invoices are numbered `TEST…` and orders carry a yellow "PROBĂ" pill; these are real app states, left as they are. The yellow Test-mode banner is hidden in the screenshots except in screenshot 4 (the Test-mode screen), because a live store does not show it. One state is staged in the throwaway database: order #1116 carries the customer typo "Volutari" and FAN Courier's rejection with "Ai vrut: Voluntari, Pipera (Voluntari), Luparia?". The text is produced by the app's own `localityError()` run on FAN Courier's public locality list for Ilfov; the demo has no courier account, so the real courier call cannot happen in demo mode. Customer names, addresses and phones are the app's fictional demo data.

## Where each asset goes in the Partner Dashboard

Partner Dashboard → Apps → Expedo → Distribution → Shopify App Store → **Manage listing** (primary language English), plus **Translations** for Romanian if offered.

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
| `feature/feature-en.png` | 1600×900, 99 KB | Feature image: From order to AWB, invoice and collected cash | **Feature media** (static image), English (primary) listing |
| `screenshots/en/01-dashboard.png` | 1600×900, 221 KB | Screenshot 1: See what needs doing today | **Desktop screenshots**, position 1, English (primary) listing |
| `screenshots/en/02-address-check.png` | 1600×900, 142 KB | Screenshot 2: Fix the address before the courier rejects it | **Desktop screenshots**, position 2, English (primary) listing |
| `screenshots/en/03-bulk-awb-invoice.png` | 1600×900, 258 KB | Screenshot 3: AWB and invoice for many orders at once | **Desktop screenshots**, position 3, English (primary) listing |
| `screenshots/en/04-rules-test-mode.png` | 1600×900, 197 KB | Screenshot 4: Your rules, tried safely in test mode | **Desktop screenshots**, position 4, English (primary) listing |
| `screenshots/en/05-tracking-cod.png` | 1600×900, 163 KB | Screenshot 5: Track every parcel until the cash is in | **Desktop screenshots**, position 5, English (primary) listing |
| `screenshots/en/06-couriers-invoicing.png` | 1600×900, 140 KB | Screenshot 6: Connect your couriers and invoicing | **Desktop screenshots**, position 6, English (primary) listing |
| `screenshots/en/mobile/m1-dashboard.png` | 900×1600, 162 KB | Mobile screenshot 1: Today's orders, on your phone too | **Mobile screenshots**, position 1, English (primary) listing |
| `screenshots/en/mobile/m2-order.png` | 900×1600, 182 KB | Mobile screenshot 2: Fix an address from anywhere | **Mobile screenshots**, position 2, English (primary) listing |
| `screenshots/en/mobile/m3-delivered.png` | 900×1600, 172 KB | Mobile screenshot 3: Delivered and cash collected, at a glance | **Mobile screenshots**, position 3, English (primary) listing |
| `feature/feature-ro.png` | 1600×900, 106 KB | Feature image: De la comandă la AWB, factură și ramburs încasat | **Feature media** (static image), Romanian listing / translation |
| `screenshots/ro/01-dashboard.png` | 1600×900, 220 KB | Screenshot 1: Vezi dintr-o privire ce ai de făcut azi | **Desktop screenshots**, position 1, Romanian listing / translation |
| `screenshots/ro/02-address-check.png` | 1600×900, 140 KB | Screenshot 2: Adresa greșită, prinsă înainte de curier | **Desktop screenshots**, position 2, Romanian listing / translation |
| `screenshots/ro/03-bulk-awb-invoice.png` | 1600×900, 262 KB | Screenshot 3: AWB și factură pentru mai multe comenzi deodată | **Desktop screenshots**, position 3, Romanian listing / translation |
| `screenshots/ro/04-rules-test-mode.png` | 1600×900, 200 KB | Screenshot 4: Regulile tale, verificate în modul de probă | **Desktop screenshots**, position 4, Romanian listing / translation |
| `screenshots/ro/05-tracking-cod.png` | 1600×900, 164 KB | Screenshot 5: Urmărești coletul până încasezi rambursul | **Desktop screenshots**, position 5, Romanian listing / translation |
| `screenshots/ro/06-couriers-invoicing.png` | 1600×900, 141 KB | Screenshot 6: Conectezi curierii și programul de facturare | **Desktop screenshots**, position 6, Romanian listing / translation |
| `screenshots/ro/mobile/m1-dashboard.png` | 900×1600, 161 KB | Mobile screenshot 1: Comenzile de azi, și pe telefon | **Mobile screenshots**, position 1, Romanian listing / translation |
| `screenshots/ro/mobile/m2-order.png` | 900×1600, 181 KB | Mobile screenshot 2: Corectezi adresa de oriunde | **Mobile screenshots**, position 2, Romanian listing / translation |
| `screenshots/ro/mobile/m3-delivered.png` | 900×1600, 168 KB | Mobile screenshot 3: Livrat și încasat, dintr-o privire | **Mobile screenshots**, position 3, Romanian listing / translation |
| `screenshots/labels-sample.pdf` | 3 KB | The labels PDF rendered in screenshot 3 (test labels) | Reference only |
| `review/expedo-review-screencast.mp4` | 1920×1080, 2:36, 4.9 MB | Screencast for review: real walkthrough of the demo UI, English captions burned in, H.264 CRF 23 | **Testing instructions → screencast** (upload, or unlisted video link) |
| `review/expedo-review-screencast.en.srt` | 4 KB | The screencast captions as subtitles | Optional: subtitles if uploaded to YouTube/Vimeo |
| `review/screencast-chapters.json` | 4 KB | Caption timestamps | Reference for the reviewer notes |
<!-- assets:end -->

## Listing fields that are not files

| Field | Value | Notes |
|---|---|---|
| App name | `Expedo` | Must stay similar to `name` in `shopify.app.toml` (req. 4.1.1). Short names don't truncate in the admin nav. |
| App card subtitle, introduction, details, features, search terms | `LISTING-COPY.en.md` / `.ro.md` | Character counts next to each field. |
| Screenshot / feature image alt text | `LISTING-COPY.*.md` | Required by Shopify for every image. |
| Feature media | Static image `feature/feature-en.png` | No promotional video yet. If one is made later: 2–3 min, promotional, screencast parts ≤ 25 %. Don't use the review screencast here. |
| Demo store URL | Leave empty, or a development store | Expedo has nothing on the storefront; a storefront link wouldn't show the app. |
| Integrations (max 6) | **Cargus, Sameday, FAN Courier, SmartBill, Oblio, FGO** (recommended) | All eight are direct integrations: Cargus, Sameday, FAN Courier, GLS, DPD, SmartBill, FGO, Oblio. Names only, no logos. Swap in GLS / DPD if your merchants use them more. |
| Languages | **Romanian** | Only languages the app UI is usable in (req. 4.3.2). The English listing text is fine; the details say the interface is Romanian. |
| Categories | Primary: **Orders and shipping › Shipping solutions › Shipping**. Secondary, if offered: **Orders and shipping › Orders › Invoices and receipts** (or **Order tracking**) | Pick the structured features that are true (labels, carriers, tracking, invoices). Taxonomy read from apps.shopify.com on 2026-10-02. |
| Install eligibility | Geography: **Romania** (store country / ships to Romania); currency RON | Req. 4.3.8: the couriers and invoicing apps only work for Romania. Sales channel: Online Store **not** required (works with any order source). |
| Works with | Shopify admin (embedded app); order sources: any channel | — |
| Privacy policy URL | `https://<app-host>/privacy` (EN), `https://<app-host>/confidentialitate` (RO) | Required. Served by the app once deployed. |
| Support | E-mail `office@krea.ro`; optional FAQ / docs page (dedicated pages, not cloud documents) | — |
| Testing instructions | Block "Paste into Testing instructions" in REVIEW-INSTRUCTIONS.md | Attach or link the full file and the screencast. |
| Screencast | `review/expedo-review-screencast.mp4` | Upload (or unlisted YouTube/Vimeo link if the form asks for a URL). |

## Pricing: DRAFT, owner decides

Nothing below is final; no price appears anywhere else in the kit (req. 4.2). Shopify notes: plans show lowest to highest; a free trial (14 days recommended) must be stated; with a free and a paid plan choose **Recurring charge**; extra charges go in "Description of additional charges". **The app has no billing code yet**: use Shopify **managed pricing** (plans defined in the Partner Dashboard, no code) or add the Billing API before submitting a paid plan.

| Option | Plans | Good when |
|---|---|---|
| A. Free + paid | **Free**: Test mode unlimited, up to `[N]` live orders/month, all couriers and invoicing apps. **Pro** `[price]/month`: unlimited live orders, 14-day free trial | You want installs and reviews early; Test mode lets merchants judge it before paying. |
| B. One paid plan | **Expedo** `[price]/month`, 14-day free trial, everything included | Simplest to explain and to support. |
| C. Tiers by monthly orders | **Start** up to `[N1]` live orders, **Growth** up to `[N2]`, **Unlimited**; same features in all, 14-day trial | Shops differ a lot in volume; price follows the work done. |

Count only orders that get a real AWB (live), so Test mode stays free in every option.

## Protected customer data request (level 2)

Partner Dashboard → Apps → Expedo → API access requests → Protected customer data → Request access. Select **Name, Address, Phone, Email**. Reasons to paste:

- **Name and address:** printed on the courier AWB (shipping label) and on the invoice the merchant issues for the order.
- **Phone:** required by Romanian couriers to deliver; the courier calls the recipient.
- **Email:** passed to the merchant's invoicing app as the client's e-mail on the invoice; the invoicing app e-mails the invoice only if the merchant turns that on. Not used for marketing.
- Data comes from orders only (no `read_customers`), is used only to ship and invoice the order, and is deleted on `customers/redact` and `shop/redact`.

Then complete the data protection details (level 1 and 2 requirements, see REQUIREMENTS.md).

## Owner checklist

- [ ] Deploy the app on its final host; set `application_url` / `redirect_urls` / `client_id` in `shopify.app.toml`; `shopify app deploy`.
- [ ] Check that `https://<app-host>/privacy` and `/confidentialitate` are live; put the URL in the listing.
- [ ] Upload `icon/expedo-icon-1200.png` in the app configuration (Dev Dashboard) and in the listing.
- [ ] Paste EN copy from `LISTING-COPY.en.md`; add the Romanian translation from `LISTING-COPY.ro.md` if Romanian is available for custom translations. Check the subtitle counter in the form (62).
- [ ] Upload `feature/feature-en.png`, the six `screenshots/en/*.png` in order 01–06, and the three `screenshots/en/mobile/*.png`; paste each alt text. Use the `ro/` set for the Romanian listing if the form allows per-language images.
- [ ] Decide pricing (option A, B or C), set it up via managed pricing or Billing API, then fill the Pricing section. No prices in images.
- [ ] Pick the 6 integrations, categories and structured features; set Languages = Romanian; install eligibility = Romania.
- [ ] Request protected customer data (level 2: name, address, phone, email) with the reasons above; complete data protection details.
- [ ] Add the emergency developer contact (Partner account settings).
- [ ] Fill the OWNER parts of REVIEW-INSTRUCTIONS.md (FAN Courier public test account, FGO test environment account, optional hosted demo URL + password) or delete them.
- [ ] Screencast: step 1 (install) is shown as a title card because there was no deployed app or development store here. Shopify asks the screencast to show onboarding, so after deploying, consider recording the real install on a development store (≈ 15 s) and placing it after the intro card.
- [ ] Add the feature "Warning when a customer has refused parcels before" (in `copy.mjs` → `featuresPending`) to the listing only once it is live, then rebuild (`build.mjs copy`).
- [ ] Re-read REQUIREMENTS.md sources right before submitting; Shopify updates them.
