# Expedo — Shopify order processing for Romania

Expedo takes the orders from Shopify and does the rest: checks the address, creates the shipping label (AWB) with the courier, issues the invoice, marks the order as fulfilled in Shopify (the customer gets the AWB by email), tracks the parcel and, once it's delivered, marks the cash on delivery (COD) as collected. It does the same job as xConnector, built starting from the errors we see there.

The app is in English, with Romanian as the second language (see [Languages](#languages)).

## Why it's better than xConnector

| Problem with xConnector | What Expedo does |
|---|---|
| Cargus AWBs fail without saying why | The address is checked **before** the courier (county, city, sector, phone, postal code). The city is looked up in the courier's list of places; if it doesn't match, you see "Did you mean: X, Y, Z?" and fix it in one click. |
| FGO invoicing says "hashtag not found" | The FGO hash is computed exactly as their documentation says (v7.0, March 2026), with automated tests. Requests are sent as JSON, as FGO now requires. |
| Technical errors, raw JSON | Every error has a short message + what to do, in the merchant's language. Technical details stay under "Technical details". |
| Temporary errors (courier down) = stuck order | Retried automatically after 1, 5, 15, 60, 180 minutes. |
| Risk of a duplicate AWB or invoice | An order never gets two AWBs or two invoices (a lock per order + a check in the database). |
| Test invoices on real orders | **Test mode**: the whole flow runs on real orders, but with a test courier and test invoicing; Shopify isn't touched. |
| One courier per store | **Rules**: easybox → Sameday, over 5 kg → 2 parcels, COD over RON 1,500 → on hold, etc. |

Also: labels for many orders in one PDF (A6 or A4), a picking list, a COD export (CSV) to reconcile courier payouts, a full history on every order, a dashboard with what needs doing today, and the **refusal history**: if a customer refused a COD parcel before, their new order shows "The customer refused 2 parcels before (out of 5)" before the AWB (and you can make a rule "Parcels refused before > 0 → on hold").

## Customer data

- Names, addresses, phone numbers and emails are **encrypted** in the database (AES-256-GCM, key from `APP_SECRET`). Search by name / phone / email works through codes (HMAC), exact matches only; order number, AWB and invoice are searched as before. Older databases are encrypted on their own at first start.
- **Settings → Customer data**: how many days customer data is kept after delivery / return / cancellation (90, 180, 365, 730; default 180). It's deleted daily; the order number, amounts, AWB and invoice remain. Orders in progress aren't touched.
- **Activity → Data access**: who opened an order or downloaded labels, invoices, the picking list, the COD export, customer data (kept one year).
- Shopify GDPR requests (customer data, customer deletion, store deletion) are handled automatically; a data request shows up in Activity with a download button.
- Public pages: `/privacy`, `/terms` (with the data processing agreement), in Romanian `/confidentialitate`, `/termeni`. The incident procedure and the answers to Shopify's questionnaire: [`docs/security.md`](docs/security.md) (Romanian: [`docs/securitate.md`](docs/securitate.md)).

## Integrations

- **Couriers:** Cargus, Sameday (including easybox), FAN Courier (including FANbox), GLS, DPD.
- **Invoicing:** SmartBill, FGO, Oblio.

The integrations are written from the official documentation and checked against the real servers with deliberately wrong login details (addresses, authentication, errors). **Successful answers (AWB created, invoice issued) haven't been seen on a real account yet** (we don't have the login details here). Uncertain spots are marked in the code with `// VERIFY:`. First step for each: "Test connection" in Settings, then an order in test mode, then a real one.

## Languages

English first, Romanian second. Every text the merchant sees comes from two catalogs, [`src/i18n/en.js`](src/i18n/en.js) and [`src/i18n/ro.js`](src/i18n/ro.js) (same keys; a test checks it).

- **Which language:** inside the Shopify admin, the admin user's language (App Bridge `shopify.config.locale`, or the `locale` parameter Shopify adds): Romanian if it starts with `ro`, English otherwise. In the standalone dashboard, the store setting **Settings → General → Language** (English by default; the demo store too).
- **Engine:** [`src/i18n/core.js`](src/i18n/core.js), no dependencies, shared by the server and the dashboard (served as `/i18n/core.js`; the dashboard's texts as `/i18n/<locale>.json`). `t(locale, key, params)` with `{param}` placeholders, plurals (`{ one, few, other }`, by `Intl.PluralRules`), money / date formats (`{amount, money}` → "RON 1,234.50" / "1.234,50 lei"), English fallback.
- **Errors** keep a stable `code` plus `params`; the message and the hint (`errors.<CODE>.message` / `.hint`, or an adapter's own key) are rendered when shown, in the viewer's language. What a provider says verbatim stays verbatim, quoted ("SmartBill says: “…”").
- **History** rows store a message key + params, rendered when read; rows from before keep their Romanian text.
- Adding a text: add the key to both catalogs, use `t()` (dashboard) or `m(key, params)` (server: errors, events, adapter messages). `npm test` fails on a key missing in either language or never used.

Left in Romanian on purpose: the order data itself (products, names, addresses, shipping methods come from Shopify), what couriers and invoicing apps say verbatim (quoted), their own menu names in the help texts ("SmartBill Cloud → Configurare → Serii"), the text Expedo puts on Romanian documents (invoice lines "Transport", unit "buc", "Comanda #1024", AWB contents "Produse"), and the Romanian legal pages.

## Quick start (demo, no Shopify)

```bash
npm install
npm run demo        # http://localhost:3000
```

Starts with a demo store with 21 Romanian orders, including some "problem" ones (no phone, no county, a company with a tax ID, easybox, a canceled order) and a customer who refused a COD parcel before. The demo store is in English; switch it in Settings → General → Language.

## Tests

```bash
npm test
```

## Installing on a real store

1. **Shopify app:** create the "Expedo" app in the Dev Dashboard (dev.shopify.com). Fill in `client_id` and the URLs in `shopify.app.toml`, then `shopify app deploy`.
   - The app reads names, addresses and phone numbers from orders, so it needs access to **protected customer data** (level 2: name, address, phone, email). Request it in the Partner Dashboard → API access; the questionnaire answers are in `docs/security.md`. For "Privacy policy URL" use `https://<server>/privacy`.
2. **Server:** `render.yaml` is ready for Render. **Note:** the database is SQLite, so it needs a persistent disk (Starter plan + disk, about $7/month). On the free plan the data is lost on every restart.
3. **Variables:** see `.env.example`. `APP_SECRET` encrypts customer data, courier passwords and Shopify tokens; never change it after the first start. `PUBLISHER_DETAILS` (tax ID, registered office) appears on the privacy and terms pages.
4. Install the app on the store → it opens in the Shopify admin → **Settings → Couriers** and **Invoicing**: login details + "Test connection".
5. Run a few days in **test mode**, then **Settings → General → Live**.

## How it's built

- Node 22, Express, SQLite (`node:sqlite`), no build step for the dashboard.
- `src/core/` — address validation, rules, the processing flow (`pipeline.js`).
- `src/couriers/`, `src/invoicing/` — one file per integration, all on the same contract (`contract.js`).
- `src/i18n/` — the catalogs (English, Romanian) and the translation engine.
- `src/shopify/` — OAuth, token exchange for the embedded app, webhooks, GraphQL Admin API (2026-07).
- `src/worker.js` — background jobs (automatic processing, parcel tracking every 30 min, re-sync every 15 min), saved in the database, so nothing is lost on restart.
- `public/` — the dashboard (HTML + plain JS). Works inside the Shopify admin (App Bridge) and on its own, with a password (`ADMIN_PASSWORD`).

## Testing on a development store

```bash
SHOPIFY_API_KEY=... SHOPIFY_API_SECRET=... node scripts/e2e-devstore.mjs <store>.myshopify.com
```

The app must be created in the Dev Dashboard by the same organization as the store, installed on it, and have access to customer data (Partners → API access requests). The script creates 3 test orders and checks the whole flow in Shopify, without emails to customers. Your own stores can also be connected permanently through `SHOPIFY_OWN_STORES`.
