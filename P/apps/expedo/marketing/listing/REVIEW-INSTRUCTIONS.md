# Expedo: instructions for the Shopify app review

For the Partner Dashboard submission: the short block in **"Paste into Testing instructions"** below goes into the form; this whole file can be linked or attached as the detailed version. The screencast `review/expedo-review-screencast.mp4` (2:36, 1920×1080, English captions burned in, `expedo-review-screencast.en.srt` alongside) follows the same steps.

## What Expedo does, in one paragraph

Expedo is an embedded admin app for stores that ship within Romania. It imports orders, checks the delivery address before anything goes to a courier, creates the AWB (shipping label) at Cargus, Sameday, FAN Courier, GLS or DPD, issues the invoice in SmartBill, FGO or Oblio, marks the order fulfilled in Shopify with the tracking number (Shopify sends its shipping e-mail), tracks the parcel and, when a cash-on-delivery parcel is delivered, marks it collected. **The app's interface is in Romanian**; button names below are given in Romanian with the English meaning.

## No courier or invoicing account needed: Test mode

Every new store starts in **Test mode** ("Mod de probă", yellow banner at the top). In Test mode Expedo runs the whole flow on the store's real orders but replaces every courier and invoicing app with built-in test providers: AWBs and invoices are numbered `TEST…`, labels say "ETICHETA DE PROBA - NU SE EXPEDIAZA", nothing is sent to couriers or invoicing apps, and **Shopify is not modified** (no fulfillment, no tags, no payment). This is the mode to review in.

## Before you start: test orders on the development store

Expedo imports the last 14 days of orders on install and every new order after that (webhooks). Create 3 orders with a **Romanian** shipping address, before or after installing:

| Order | How to create it | Shipping address (Romania) |
|---|---|---|
| A, card | Admin → Orders → Create order → any product → customer → "Collect payment → Mark as paid" | Name *Andreea Popescu*, Str. Observatorului 112, ap. 14, *Cluj-Napoca*, county *Cluj*, 400394, phone 0745 123 456 |
| B, cash on delivery | Settings → Payments → Manual payment methods → add **"Cash on Delivery (COD)"**, then place an order on the storefront and pick it at checkout | Bd. Unirii 45, bl. E3, *București*, county *București*, postal code 030167 (sector 3), phone +40 722 334 455 |
| C, problem: no phone | Like A, but leave the phone empty | any Romanian address |

Expected after import (once a default courier is chosen in step 2): A and B are **"Gata de procesat"** (Ready); C is **"Necesită atenție"** (Needs attention) with a red explanation: "Lipsește telefonul destinatarului." (recipient phone missing) and what to do. Other checks work the same way, e.g. "Lipsește județul." (county missing) or a Bucharest address without sector.

## Step by step

Each step says what to do and what you should see.

1. **Install.** Open the install link for your development store and approve access to orders and merchant-managed fulfillment orders. *Expected:* Expedo opens inside the admin (Apps → Expedo) on **"Panou"** (Dashboard), with the yellow Test-mode banner. Orders appear within a few seconds; if not, Comenzi → **"Sincronizează cu Shopify"** (Sync with Shopify). Until a courier is chosen (step 2) every order says "Nu e ales niciun curier." (no courier chosen).
2. **Choose a courier and an invoicing app (no credentials in Test mode).** Setări (Settings) → **Curieri** → click e.g. **Sameday** → **"Salvează"** (Save) with the fields empty → **"Folosește ca implicit"** (Use as default). Then Setări → **Facturare** → **SmartBill** → "Salvează" → "Folosește ca implicit". *Expected:* green confirmation; the provider card shows "implicit" (default). On a live store the merchant would enter the API credentials here and click **"Testează conexiunea"** (Test connection).
3. **Dashboard.** Panou shows orders to process, orders needing attention, parcels on the way and cash on delivery to collect.
4. **Fix an address.** Comenzi (Orders) → tab **"Necesită atenție"** → click order C → in **"Adresa de livrare"** type a phone number in **Telefon** (e.g. 0721 888 999), then **"Salvează adresa"** (Save address). *Expected:* "Adresa a fost salvată și verificată din nou." (address saved and checked again); the order moves to "Gata de procesat". The edit stays in Expedo and does not change the order in Shopify.
5. **One order: AWB + invoice.** Open order A → **"Generează AWB + factură"** (Generate AWB + invoice). *Expected:* a toast with the AWB number and invoice number (`TEST…`), status **"Expediată"** (Shipped), buttons **"Eticheta AWB"** (label PDF) and **"Factura PDF"**.
6. **Bulk.** Tab **"Gata de procesat"** → tick the header checkbox → in the dark bar at the bottom click **"Generează AWB + factură"**. *Expected:* "Gata: N comenzi procesate." and the list of those orders with AWB and invoice columns filled. Click the same button again on those orders: no second AWB or invoice is created.
7. **Labels and picking list.** With the processed orders still selected: **"Etichete"** downloads one PDF with all labels (A6 by default; A4 in Setări → Colete). **"Listă de picking"** opens a printable list of products to pick.
8. **Tracking and cash on delivery.** Test AWBs advance one status every 2 minutes. After about 8–10 minutes, Panou → **"Verifică coletele"** (Check parcels). *Expected:* order B shows **"Livrată"** (Delivered); open it: under Plată (Payment) a green badge **"încasat"** (collected), and the history ("Istoric") lists AWB, invoice, delivery and cash collected. In Test mode Shopify is not changed; on Live the order is also marked paid in Shopify and the payment is recorded on the invoice.
9. **Rules.** Setări → **Reguli** (Rules): add a rule, e.g. *Metoda de livrare conține "easybox"* → *Curier: Sameday*. Rules are re-applied to open orders when saved.
10. **Errors in plain Romanian.** Any failed step shows a short message plus what to do; technical details stay under "Detalii tehnice". **Activitate** (Activity) lists everything that happened.
11. **Cash-on-delivery export.** Panou → **"Export ramburs (CSV)"** downloads COD amounts per parcel.
12. **Live mode (optional).** Setări → General → **Live** turns on real AWBs, real invoices and the Shopify fulfillment with tracking (customer gets Shopify's shipping e-mail). It needs real courier and invoicing credentials; see "Full live test" below.

### What can only be seen with a real courier account

The **"Ai vrut: X, Y, Z?"** (Did you mean…?) suggestions come from the courier's own list of localities, which is checked only when a real courier is called. In Test mode you will see the checks Expedo does itself (county, Bucharest sector, phone, postal code). The screencast (0:01:14) shows the courier suggestion with FAN Courier's public locality list.

### Full live test (optional, if you want to see the Shopify fulfillment)

> OWNER: fill in before submitting, or delete this section.
>
> - FAN Courier: the public test account published in FAN Courier's API documentation (EN_FANCourier_API, p. 4): username `…`, password `…`, client ID `…`. In Expedo: Setări → Curieri → FAN Courier.
> - FGO test environment: an account created at testuat.fgo.ro: CUI `…`, private key `…`, series `…`; tick **"Mediu de test FGO"**. In Expedo: Setări → Facturare → FGO.
> - Then Setări → General → Live, and repeat step 5 on a new order. Expected: the order is fulfilled in Shopify with the FAN AWB as tracking number.

## Demo store data

Besides the reviewer's own development store, the app has a built-in demo store ("Magazin demo (jucării)") with **19 Romanian orders**, including problem orders (no phone, no county, company with CUI, easybox delivery, cancelled order). It runs only in demo mode (`DEMO=1`) and always stays in Test mode. It is what the screenshots and the screencast show.

> OWNER (optional): if you host a demo instance for reviewers, run a separate server with `DEMO=1` and `ADMIN_PASSWORD=<password>` on its own database (never the production one) and add here: URL `https://…`, password `…`.

## Data and privacy

Expedo reads, from orders only: shipping/billing name, address, phone, e-mail, products, totals, payment gateway (to detect cash on delivery). It uses them to create the AWB and the invoice and to track the parcel. Courier/invoicing credentials and the Shopify token are stored encrypted. Mandatory compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`) are implemented. Privacy policy: `https://<app-host>/privacy` (English) and `/confidentialitate` (Romanian).

Support: **office@krea.ro** · Publisher: ARTEMIS DIGITAL SRL

---

## Paste into "Testing instructions"

```
Expedo is an embedded admin app for stores shipping within Romania (UI in Romanian; the attached screencast has English captions and follows these steps).

No courier or invoicing account is needed: new stores start in TEST MODE (yellow banner). AWBs and invoices are test documents, nothing is sent to couriers or invoicing apps, and Shopify is not modified.

1. Create 2-3 orders with a Romanian shipping address (e.g. Cluj-Napoca, county Cluj, 400394, phone 0745123456). For cash on delivery, add the manual payment method "Cash on Delivery (COD)" and order on the storefront. Leave the phone empty on one order to see an address problem.
2. Install, open Apps > Expedo. Orders import automatically (or Comenzi > "Sincronizează cu Shopify").
3. Setări > Curieri > Sameday > "Salvează" (fields may stay empty in test mode) > "Folosește ca implicit". Same in Setări > Facturare > SmartBill.
4. Comenzi > "Necesită atenție": open the order without phone, add a phone, "Salvează adresa". It moves to "Gata de procesat".
5. "Gata de procesat": tick all > "Generează AWB + factură". Expected: TEST AWB + invoice per order, status "Expediată". Then "Etichete" (one PDF with all labels) and "Listă de picking".
6. After ~10 minutes: Panou > "Verifică coletele". Expected: "Livrată"; the cash-on-delivery order shows "încasat".
7. Setări > Reguli, Automatizări, General (Test/Live) show the rest. Live needs real courier/invoicing credentials (see attached instructions).

Support: office@krea.ro
```
