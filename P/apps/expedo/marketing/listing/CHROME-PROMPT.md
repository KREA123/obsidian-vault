Fill in and submit the Shopify App Store listing for my app "Expedo" in this browser. I'm logged in to Shopify Partners (organization ARTEMIS DIGITAL SRL). The listing page is:
https://apps.shopify.com/services/partner-app-submissions/f8ed5b7064a0b5d373c6bae33dd1f6b5/en
(Partner Dashboard → Apps → Expedo → Distribution → Shopify App Store → English listing.)

Work through every section in the left menu, fix all the issues in the orange box, save after each section, and tell me if something blocks you. Use exactly the texts below. Never change the client secret, never uninstall anything, and don't touch any other app.

## Uploading images and the video
Every file is online (CORS is open), so you don't need my disk:
- Icon 1200×1200: https://expedo.onrender.com/listing-kit/icon/expedo-icon-1200.png
- Feature image 1600×900: https://expedo.onrender.com/listing-kit/feature/feature.png
- Desktop screenshots 1600×900, in this order:
  1. https://expedo.onrender.com/listing-kit/screenshots/01-dashboard.png
  2. https://expedo.onrender.com/listing-kit/screenshots/02-address-check.png
  3. https://expedo.onrender.com/listing-kit/screenshots/03-bulk-awb-invoice.png
  4. https://expedo.onrender.com/listing-kit/screenshots/04-rules-test-mode.png
  5. https://expedo.onrender.com/listing-kit/screenshots/05-tracking-cod.png
  6. https://expedo.onrender.com/listing-kit/screenshots/06-couriers-invoicing.png
- Mobile screenshots 900×1600:
  1. https://expedo.onrender.com/listing-kit/screenshots/mobile/m1-dashboard.png
  2. https://expedo.onrender.com/listing-kit/screenshots/mobile/m2-refused.png
  3. https://expedo.onrender.com/listing-kit/screenshots/mobile/m3-delivered.png
- Review screencast (2:40): https://expedo.onrender.com/listing-kit/review/expedo-review-screencast.mp4

If an upload only offers a file picker, put the file into the input with JavaScript on the page, then check the preview appears:
```js
const url = '<file URL>', name = url.split('/').pop();
const blob = await (await fetch(url)).blob();
const input = document.querySelector('input[type=file]'); // the input of the field you are filling
const dt = new DataTransfer(); dt.items.add(new File([blob], name, { type: blob.type }));
input.files = dt.files; input.dispatchEvent(new Event('change', { bubbles: true }));
```
If that doesn't work for a field, tell me which one. I'll drag the file in myself.

## 1. Basic app information
- App name: `Expedo`
- App icon: if the form says it syncs from the Partner Dashboard / Dev Dashboard, open "Change in Partner Dashboard" and upload the icon there (Dev Dashboard → Apps → Expedo → Settings, or the active version's configuration). If it asks for a new version, release it, then come back.
- App category: primary **Orders and shipping › Shipping solutions** (or the closest "Shipping" category). Secondary, if offered: **Orders and shipping › Orders › Invoices and receipts** (or Order tracking). Tick the structured features that are true: shipping labels, carrier integrations, order tracking, invoices, cash on delivery.
- Languages: **English, Romanian**
- Integrations (max 6), names only: **Cargus, Sameday, FAN Courier, SmartBill, Oblio, FGO**

## 2. App store listing content
- App introduction (max 100): `Catch bad addresses before the courier does, then ship many orders with AWB and invoice at once.`
- App details (max 500): `Expedo takes each order from address check to collected cash on delivery. Before any AWB, it checks county, locality against the courier's list, Bucharest sector, phone and postal code, and suggests the right locality. It then creates the AWB at Cargus, Sameday, FAN Courier, GLS or DPD, issues the invoice in SmartBill, FGO or Oblio and marks the order fulfilled with tracking. Test mode runs it all on real orders, sending nothing. For stores shipping in Romania. English and Romanian interface.`
- Features (each max 80; add as many as allowed, in this order):
  - Address checked before the courier, with suggestions for misspelled localities
  - Warning when a customer has refused parcels before, before you create the AWB
  - AWB and invoice for many orders in one click, with every label in one PDF
  - Orders marked fulfilled in Shopify with tracking, so customers get the email
  - Parcels tracked; delivered cash-on-delivery orders marked collected and paid
  - Rules choose courier, parcels or hold, e.g. easybox orders go to Sameday
  - Test mode on real orders: test AWBs and invoices, nothing leaves the app
  - Every error explained in plain words, with what to do next
  - One AWB and one invoice per order, even after a double click
  - Temporary courier errors retried automatically, without blocking the order
  - Picking list for the warehouse and cash-on-delivery export to CSV
- Feature media: static image = feature.png. Alt text: `Expedo order with its AWB, invoice, delivered status and cash on delivery collected`
- Desktop screenshots 1–6 in order, with alt texts:
  1. `Expedo dashboard with orders to process, orders needing attention, parcels in transit and cash on delivery to collect`
  2. `Courier error for a misspelled locality with the suggestion Voluntari, and the shipping address corrected to Voluntari`
  3. `Order list with several orders selected, the Create AWB plus invoice button, a refused-parcels warning, and the labels PDF`
  4. `Rules screen with the easybox to Sameday rule, and the test mode and live mode switch`
  5. `Order history timeline from AWB to delivery, with cash on delivery marked collected`
  6. `Settings with the five couriers and the three invoicing apps, each with its connection status`
- Mobile screenshots 1–3, with alt texts:
  1. `Expedo dashboard on a phone with orders to process, orders needing attention and parcels on the way`
  2. `Order on a phone with a warning that the customer refused one parcel before, and the customer history`
  3. `Delivered order on a phone with AWB, tracking status and cash on delivery collected`
- Demo store URL: leave empty.
- Support: email `office@krea.ro`. If a support/FAQ URL is required, use `https://expedo.onrender.com/listing-kit/REVIEW-INSTRUCTIONS.md`.
- Resources: privacy policy `https://expedo.onrender.com/privacy`. Terms of service (if asked) `https://expedo.onrender.com/terms`.

## 3. Pricing details: Shopify App Pricing (Managed Pricing), NOT "Manual pricing"
Billing: recurring, USD, every 30 days. No free plan. Create two **public** plans:

| Display name | Handle (if asked) | Price | Free trial |
|---|---|---|---|
| Pro | pro | $15.00 every 30 days | 5 days |
| Pro Max | pro_max | $30.00 every 30 days | 5 days |

- Turn on **"Free for partners and developers"** (or the equivalent "free for development stores" option).
- Welcome link: `/` (if asked).
- Top features for Pro: `Up to 1,000 orders every 30 days` · `All couriers and invoicing apps` · `Address & phone check` · `Test mode` · `Bulk processing and rules` · `Tracking and COD reconciliation`
- Top features for Pro Max: `Unlimited orders` · `Everything in Pro` · `Automatic processing of new orders` · `Customer refusal history` · `COD export (CSV)` · `Multiple stores` · `Priority support`
- If any other plan exists (Free, Starter, Growth, Plus), unpublish it.

## 4. App discovery content
- App card subtitle (max 62): `Ship orders in Romania without retyping AWBs and invoices`
- Search terms (up to 5): `AWB` · `courier Romania` · `cash on delivery` · `invoicing` · `shipping labels`

## 5. Install requirements
- Sales channel requirements: the **Online Store is NOT required** (the app works in the admin only). Don't require any sales channel.
- Geographic / install eligibility, if offered: stores in **Romania** (currency RON).

## 6. Tracking information
Leave empty unless something is required.

## 7. Contact information
- Merchant review email: `office@krea.ro`
- App submission email: `office@krea.ro`

## 8. App testing information
- Test account: **not required**. The app is embedded in the Shopify admin and has no separate login. Tick the option saying no account is needed, or write: `No account needed: Expedo is an embedded app with no separate login. New stores start in Test mode, so no courier or invoicing account is required.`
- Screencast URL: `https://expedo.onrender.com/listing-kit/review/expedo-review-screencast.mp4`
- Testing instructions: paste exactly:

```
Expedo is an embedded admin app for stores shipping within Romania. UI in English (Romanian available). The attached screencast follows these steps.

No courier or invoicing account is needed: new stores start in TEST MODE (yellow banner). AWBs and invoices are test documents, nothing is sent to couriers or invoicing apps, and Shopify is not modified.

1. Create 2-3 orders with a Romanian shipping address (e.g. Cluj-Napoca, county Cluj, 400394, phone 0745123456). For cash on delivery, add the manual payment method "Cash on Delivery (COD)" and order on the storefront. Leave the phone empty on one order to see an address problem.
2. Install and pick the Pro Max plan (5-day free trial; free on development stores). Open Apps > Expedo. Orders import automatically (or Orders > "Sync with Shopify").
3. Settings > Couriers > Sameday > "Save" (fields may stay empty in test mode) > "Use as default". Same in Settings > Invoicing > SmartBill.
4. Orders > "Needs attention": open the order without a phone, add one, "Save address". It moves to "Ready to process".
5. "Ready to process": tick all > "Create AWB + invoice". Expected: a TEST AWB + invoice per order, status "Shipped". Then "Labels" (one PDF with all labels) and "Picking list".
6. After ~10 minutes: Dashboard > "Check parcels". Expected: "Delivered"; the cash-on-delivery order shows "collected".
7. Settings > Rules, Automation, General (Test/Live, Language) show the rest. Live needs the merchant's own courier/invoicing credentials.

Full instructions: https://expedo.onrender.com/listing-kit/REVIEW-INSTRUCTIONS.md

Support: office@krea.ro
```

## 9. Back on the "App Store review" page (Distribution)
https://partners.shopify.com/5176084/apps/430735130625/distribution/app-store
- Primary listing language: **English**.
- Protected customer data: click **Complete**. Do NOT tick "My app won't use customer data". Request the protected customer data fields **Name, Address, Phone, Email**. Reasons:
  - Name and address: printed on the courier AWB (shipping label) and on the invoice the merchant issues for the order.
  - Phone: required by Romanian couriers to deliver; the courier calls the recipient. Also used, with the e-mail, to recognise a returning customer for the refused-parcel warning in the same store.
  - Email: passed to the merchant's invoicing app as the client's e-mail on the invoice. Not used for marketing.

  Data protection answers: yes to everything that describes what the app does. Data is processed only for the stated purposes and kept minimal (from orders only, no read_customers). Customers' privacy and consent are respected through the merchant's privacy policy. Retention: deleted after a merchant-set period (default 180 days) and on customers/redact and shop/redact. Encrypted at rest (AES-256-GCM) and in transit (HTTPS/TLS). Backups are encrypted. Test and production data are separate. There is a data-loss-prevention strategy. Staff access is limited and logged (access log in the app). Strong passwords. A security incident response policy exists. If something doesn't fit these answers, stop and tell me the question.
- Run the automated checks when they unlock, and tell me the result of each one.
- App capabilities: tick what applies (orders, fulfillment, shipping); embedded app in the admin.
- When everything is green, click **Submit for review** and tell me what Shopify says. If it asks for a fee or a payment, STOP and tell me. Don't pay anything.
