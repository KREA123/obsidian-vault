# Expedo: instructions for the Shopify app review

For the Partner Dashboard submission: the short block in **"Paste into Testing instructions"** below goes into the form; this whole file can be linked or attached as the detailed version. The screencast `review/expedo-review-screencast.mp4` (2:40, 1920×1080, English UI, English captions burned in, `expedo-review-screencast.en.srt` alongside) follows the same steps.

## What Expedo does, in one paragraph

Expedo is an embedded admin app for stores that ship within Romania. It imports orders, checks the delivery address before anything goes to a courier, warns when a customer has refused parcels before, creates the AWB (shipping label) at Cargus, Sameday, FAN Courier, GLS or DPD, issues the invoice in SmartBill, FGO or Oblio, marks the order fulfilled in Shopify with the tracking number (Shopify sends its shipping e-mail), tracks the parcel and, when a cash-on-delivery parcel is delivered, marks it collected. The interface is in English (default) and Romanian (Settings → General → Language; inside the Shopify admin it follows the admin language).

## No courier or invoicing account needed: Test mode

Every new store starts in **Test mode** (yellow banner at the top). In Test mode Expedo runs the whole flow on the store's real orders but replaces every courier and invoicing app with built-in test providers: AWBs and invoices are numbered `TEST…`, labels say "TEST LABEL - DO NOT SHIP", nothing is sent to couriers or invoicing apps, and **Shopify is not modified** (no fulfillment, no tags, no payment). This is the mode to review in. Test-mode AWBs never count toward a plan's order limit.

## Plan

Expedo uses Shopify App Pricing with two plans, **Pro** and **Pro Max**, each with a **5-day free trial**; there is no free plan. Both plans are free for partners and developers, so on a development store either can be picked at no charge. **Pick Pro Max** to see every feature (the refused-parcel warning, automatic processing and the cash-on-delivery CSV export are on Pro Max). Without a plan, Test mode still works but the dashboard shows a "Choose a plan — 5-day free trial" banner.

## Before you start: test orders on the development store

Expedo imports the last 14 days of orders on install and every new order after that (webhooks). Create 3 orders with a **Romanian** shipping address, before or after installing:

| Order | How to create it | Shipping address (Romania) |
|---|---|---|
| A, card | Admin → Orders → Create order → any product → customer → "Collect payment → Mark as paid" | Name *Andreea Popescu*, Str. Observatorului 112, ap. 14, *Cluj-Napoca*, county *Cluj*, 400394, phone 0745 123 456 |
| B, cash on delivery | Settings → Payments → Manual payment methods → add **"Cash on Delivery (COD)"**, then place an order on the storefront and pick it at checkout | Bd. Unirii 45, bl. E3, *București*, county *București*, postal code 030167 (sector 3), phone +40 722 334 455 |
| C, problem: no phone | Like A, but leave the phone empty | any Romanian address |

Expected after import (once a default courier is chosen in step 3): A and B are **"Ready to process"**; C is **"Needs attention"** with a red explanation, "The recipient's phone number is missing.", and what to do. Other checks work the same way, e.g. "The county is missing." or a Bucharest address without a sector.

## Step by step

Each step says what to do and what you should see.

1. **Install.** Open the install link for your development store and approve access to orders and merchant-managed fulfillment orders.
2. **Pick a plan.** On Shopify's plan page choose **Pro Max** (5-day free trial; no charge on development stores). *Expected:* Expedo opens inside the admin (Apps → Expedo) on the **Dashboard**, with the yellow Test-mode banner. Orders appear within a few seconds; if not, Orders → **"Sync with Shopify"**. Until a courier is chosen (step 3) every order says that no courier is chosen.
3. **Choose a courier and an invoicing app (no credentials in Test mode).** Settings → **Couriers** → click e.g. **Sameday** → **"Save"** with the fields empty → **"Use as default"**. Then Settings → **Invoicing** → **SmartBill** → "Save" → "Use as default". *Expected:* a green confirmation; the provider card shows "default". On a live store the merchant would enter the API credentials here and click **"Test connection"**.
4. **Dashboard.** Shows orders to process, orders needing attention, parcels on the way and cash on delivery to collect.
5. **Fix an address.** Orders → tab **"Needs attention"** → click order C → in **"Shipping address"** type a phone number in **Phone** (e.g. 0721 888 999) → **"Save address"**. *Expected:* "Address saved and checked again."; the order moves to "Ready to process". The edit stays in Expedo and does not change the order in Shopify.
6. **One order: AWB + invoice.** Open order A → **"Create AWB + invoice"**. *Expected:* a toast with the AWB and invoice numbers (`TEST…`), status **"Shipped"**, buttons **"AWB label"** and **"Invoice PDF"**.
7. **Bulk.** Tab **"Ready to process"** → tick the header checkbox → in the dark bar at the bottom click **"Create AWB + invoice"**. *Expected:* "Done: N orders processed." and the list of those orders with AWB and invoice filled in. Click the same button again on those orders: no second AWB or invoice is created.
8. **Labels and picking list.** With the processed orders still selected: **"Labels"** opens one PDF with all labels (A6 by default; A4 in Settings → Parcels). **"Picking list"** opens a printable list of products to pick.
9. **Tracking and cash on delivery.** Test AWBs advance one status every 2 minutes. After about 8–10 minutes, Dashboard → **"Check parcels"**. *Expected:* order B shows **"Delivered"**; open it: under Payment a green **"collected"** badge, and the **History** lists AWB, invoice, delivery and cash collected. In Test mode Shopify is not changed; on Live the order is also marked paid in Shopify and the payment is recorded on the invoice.
10. **Rules.** Settings → **Rules**: e.g. *Shipping method contains "easybox"* → *Courier: Sameday*. Rules are re-checked on open orders when saved.
11. **Errors in plain words.** Any failed step shows a short message plus what to do; technical details stay under "Technical details". **Activity** lists everything that happened.
12. **Cash-on-delivery export.** Dashboard → **"COD export (CSV)"** downloads COD amounts per parcel.
13. **Live mode (optional).** Settings → General → **Live** turns on real AWBs, real invoices and the Shopify fulfillment with tracking (the customer gets Shopify's shipping e-mail). It needs real courier and invoicing credentials; see "Full live test" below.

### What needs history or a real courier account

- **Refused-parcel warning** ("The customer refused 1 parcel before (out of 2). Call them before creating the AWB, or ask for card payment.") appears when the same phone or e-mail had an earlier order that came back refused. On a fresh development store there is no such history; the screencast (1:29) and screenshot 3 show it on the demo data.
- **"Did you mean: X, Y, Z?"** suggestions come from the courier's own list of localities, which is checked only when a real courier is called. In Test mode you see the checks Expedo does itself (county, Bucharest sector, phone, postal code). The screencast (1:14) shows the courier suggestion built from FAN Courier's public locality list.

### Live mode

Live mode needs the merchant's own courier and invoicing accounts (API credentials from Cargus, Sameday, FAN Courier, GLS or DPD and from SmartBill, FGO or Oblio); Expedo has no shared test account to hand out. Everything Live does is shown in Test mode first, except the calls to those providers and the Shopify fulfillment with tracking. After entering credentials, **"Test connection"** in Settings checks them, and Settings → General → **Live** switches over.

## Demo store data

Besides the reviewer's own development store, the app has a built-in demo store ("Demo store (toys)") with Romanian demo orders, including problem orders (no phone, no county, company with a VAT code, easybox delivery, cancelled order, a customer who refused a parcel before). It runs only in demo mode (`DEMO=1`) and always stays in Test mode. It is what the screenshots and the screencast show.


## Data and privacy

Expedo reads, from orders only: shipping/billing name, address, phone, e-mail, products, totals, payment gateway (to detect cash on delivery). It uses them to create the AWB and the invoice, to track the parcel and to warn about earlier refusals in the same store. Customer data, courier/invoicing credentials and the Shopify token are stored encrypted; customer data of finished orders is removed after the retention period set in Settings → Customer data. Mandatory compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`) are implemented. Privacy policy: https://expedo.onrender.com/privacy.

Support: **office@krea.ro** · Publisher: ARTEMIS DIGITAL SRL

---

## Paste into "Testing instructions"

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
