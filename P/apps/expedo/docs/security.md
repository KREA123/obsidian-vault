# Security and data protection — Expedo

Published by **ARTEMIS DIGITAL SRL** · contact: office@krea.ro · updated: October 2, 2026 · Română: [`securitate.md`](securitate.md)

This document has three parts: what data we keep and how we protect it (in short), the security incident procedure, and the answers to Shopify's "Protected customer data" questionnaire. The public pages that tell merchants and customers the same things: `/privacy` (`/confidentialitate`) and `/terms` (`/termeni`, with the data processing agreement).

## 1. What data we keep and where

| Where | What it holds | How it's protected |
|---|---|---|
| `orders.data` | the Shopify order: names, addresses, phone, email, company/tax ID, products, amounts, note, checkout attributes | encrypted (AES-256-GCM, `enc1:`) |
| `orders.overrides` | manual fixes (address, phone, notes on the AWB) | encrypted |
| `orders.issues`, `orders.last_error` | validation issues (may quote the phone number), courier errors; stored as a message key + params | encrypted |
| `orders.phone_hash`, `email_hash`, `search_terms` | codes for search and the refusal history | keyed HMAC, per store; can't be reversed without `APP_SECRET` |
| `orders` (other columns) | order number (#1024), amounts, courier, AWB, invoice, statuses, dates | plaintext — not customer data |
| `events.message`, `events.params`, `events.data` | the order history: the message key (`events.key`, plaintext, e.g. `events.awbCreated`) and its params (may quote the address or phone); older rows hold the full text | encrypted (the message key holds no data) |
| `cache` | courier lists of places; for the test courier, the "created" parcels (with recipient) | encrypted |
| `stores.access_token`, `integrations.credentials` | Shopify token, courier and invoicing passwords | encrypted (already before) |
| `access_log` | who saw / exported data: Shopify user ID or "admin", action, order number | no customer data |
| `jobs` | background tasks (IDs only) | deleted after 7 days |

- The encryption key and the key for the search codes are derived from `APP_SECRET` (two different keys). `APP_SECRET` lives in the server's environment variables, not in the database.
- Rows written by older versions (plaintext) are encrypted automatically on the first start of the new version (`encryptPlaintextRows` in `src/db.js`).
- Search: order number, AWB and invoice are searched as before (partial match). Name, phone and email are matched exactly only (whole words of the name, the phone in any format, the email case-insensitively), through the codes.
- Transfer: HTTPS to Shopify, couriers and invoicing apps; HTTPS at the host (Render). Server: Render, Frankfurt region (`render.yaml`).

**Retention (`src/core/privacy.js`):** daily, for finished orders (delivered, returned, canceled, fulfilled outside Expedo) older than the store setting "Keep customer data" (90 / 180 / 365 / 730 days, default 180, counted from delivery / return / cancellation), we delete: names, addresses, phone, email, company, note, attributes, tags, address fixes, issues, errors, search codes; from the history, errors and manual edits are deleted, and the details of the other events. What remains: order number, amounts, products, courier, AWB, invoice, statuses. Orders in progress, or being processed at that moment, are never touched. The access log is kept 365 days.

**GDPR webhooks:**
- `customers/data_request` — recorded in the access log (actor "shopify") and in Activity (warning); the merchant clicks "Download customer data" and gets a JSON file with everything we hold. Orders are found by the IDs Shopify sends and by email (not by phone: people share phones, and we must never hand someone else's order to the requester).
- `customers/redact` — same lookup; the customer's data is deleted right away (the same function as retention), only the accounting part remains.
- `shop/redact` — everything is deleted: store, orders, integrations, events, jobs, cache, access log.

## 2. Security incident procedure

An incident = any unauthorized access to, loss of or change to the data (or a serious suspicion of one): a compromised server, a leaked `APP_SECRET` / admin password / token, a copied database, a bug that shows one store's orders to another store.

Owner: the administrator of ARTEMIS DIGITAL SRL (office@krea.ro). Every step is written down with the time in the incident register (an internal document), even if the incident turns out to be minor.

1. **Detection** (hour 0 = when we find out)
   - Sources: Render alerts and logs, `/healthz`, Activity → Data access (unusual actions, unknown actors), reports from merchants, Shopify or couriers, security reports to office@krea.ro.
   - Open the register entry: what was seen, when, where.
2. **Containment** (immediately, within the first hours)
   - If the server is compromised: suspend the service in Render; keep a copy of the disk and logs for analysis (don't delete them).
   - Change whatever may have leaked: `ADMIN_PASSWORD`, `SESSION_SECRET` (logs everyone out), `SHOPIFY_API_SECRET` (Partner Dashboard → rotate), the passwords of the Render / GitHub / Shopify Partner accounts.
   - If the database may have been copied **together with** `APP_SECRET`: treat the data as exposed. Merchants change their courier and invoicing passwords (they're in the same database). Note: changing `APP_SECRET` makes the existing data unreadable — there's no re-encryption script yet (see "Still open").
   - If it's an app bug: turn off the affected feature or roll back to the previous version.
3. **Assessment** (within 24–48 hours)
   - Which stores, which orders, which fields, which period. Sources: `access_log`, `events`, Render logs, Git history.
   - Was the data encrypted and did the key stay safe? If so, the risk to customers is low (the duty to notify remains if we can't rule out access to the key).
   - Written conclusion: is this a personal data breach? What risk does it pose to customers (low / high)?
4. **Notification** (within **72 hours** of hour 0)
   - **Affected merchants** — email to the store address in Shopify: what happened, which data and how many orders, what we did, what they need to do (e.g. change courier passwords), a contact. They are the controllers: they decide on notifying ANSPDCP and their customers; we give them all the information they need.
   - **Shopify** — through the Partner Dashboard (support) / Shopify's security and privacy contact, with the same information.
   - **ANSPDCP** (dataprotection.ro) — only for data where ARTEMIS DIGITAL SRL is the controller (data about stores and users), if the incident poses a risk to them.
   - If we don't have all the information within 72 hours, we send what we have and add to it as we go.
5. **Remediation**
   - Fix the cause (code, configuration, access), with an automated test that catches the problem in the future.
   - Restart the service only after checking; watch the logs for a few days.
6. **Post-incident review** (within 2 weeks)
   - What happened, the timeline, why we didn't catch it sooner, what we change. Recorded in the register, with a summary sent to the affected merchants.
   - Update this document, the public pages and the answers below if anything changed.

## 3. Shopify "Protected customer data" requirements → implementation

Expedo asks for level 2 (name, address, phone, email). The answers are the ones we can honestly give today; "To confirm" = depends on ARTEMIS DIGITAL SRL's accounts and organization, not on the code.

### Level 1

| # | Shopify requirement | Answer | How |
|---|---|---|---|
| 1 | Do you process only the minimum data needed? | **Yes** | Scopes: `read_orders`, `write_orders`, fulfillment orders. No `read_customers`. Name, address, phone and email are needed for the AWB and the invoice; the note and checkout attributes for easybox / company tax ID. |
| 2 | Do you tell merchants what data you process and why? | **Yes** | `/privacy`, `/confidentialitate`; link in the app (footer, Settings → Customer data). |
| 3 | Do you use the data only for those purposes? | **Yes** | Only AWB, invoice, fulfillment, tracking, cash on delivery (COD), refusal history within the same store. No marketing, selling, AI, or sharing between stores. |
| 4 | Do you respect customers' consent decisions? | **Yes / not applicable** | We don't send marketing and don't use the data for anything that needs consent. |
| 5 | Do you respect customers' opt-out of data sale? | **Yes** | We don't sell data. |
| 6 | Automated decisions with legal or similar effect? | **We make no such decisions** | The refusal history only warns; a rule made by the merchant can put the order on hold for review. No order is refused automatically; a person decides. |
| 7 | Do you have privacy and data protection agreements with merchants? | **Yes** | The terms (`/terms`) include the data processing agreement (GDPR art. 28), accepted at install. |
| 8 | Do you apply retention periods? | **Yes** | Per-store setting 90/180/365/730 days (default 180), daily job `privacy_cleanup`; access log 365 days; `shop/redact` deletes everything. |
| 9 | Do you encrypt data at rest and in transit? | **Yes** | AES-256-GCM on the fields with customer data (table in section 1); HTTPS in transit. Only data without customers stays plaintext (order number, amounts, AWB, invoice, statuses). |

### Level 2

| # | Shopify requirement | Answer | How |
|---|---|---|---|
| 10 | Do you encrypt backups? | **Yes (at application level)** | Customer data is encrypted before it reaches the disk, so any copy of the database holds only ciphertext; the key isn't on disk. Encryption of Render's disk snapshots is up to Render. |
| 11 | Do you keep test and production data separate? | **Yes** | The demo store has made-up orders; automated tests use in-memory databases with made-up data; end-to-end tests run on a development store with test orders. Test mode runs on the merchant's real orders but sends nothing to couriers / invoicing apps. |
| 12 | Do you have a data loss prevention strategy? | **Partly** | Encryption, separation per store, limited retention, access log, the exports (COD CSV) hold no customer data, exporting a customer's data is recorded. We have no dedicated DLP tools. |
| 13 | Do you limit staff access to data? | **Yes** | Only the ARTEMIS DIGITAL SRL administrator has access to the server and the database. In the store, access is granted by the merchant through Shopify permissions (Expedo has no roles of its own: whoever opens the app sees the store's orders). |
| 14 | Do you require strong passwords for staff accounts? | **Partly — to confirm** | Store users log in through Shopify (Shopify's rules, including 2FA). The admin password of the standalone dashboard (`ADMIN_PASSWORD`) isn't checked by the app — use at least 16 random characters (the app warns at startup if it's shorter than 12). To confirm: 2FA on the Render, GitHub and Shopify Partner accounts. |
| 15 | Do you log access to data? | **Yes** | `access_log`: order opened, invoice PDF, labels, picking list, COD export, customer data export, GDPR requests; who (the Shopify user from the session, or "admin") and when. Visible under Activity → Data access (with filters), kept 365 days. |
| 16 | Do you have a security incident procedure? | **Yes** | Section 2 of this document. |

## 4. Still open

- **Company details** on the public pages: the tax ID and registered office of ARTEMIS DIGITAL SRL go into the `PUBLISHER_DETAILS` variable.
- **Rotating `APP_SECRET`**: there's no script yet that re-encrypts the data with a new key; until then the key can't be changed without losing the encrypted data.
- **The order list** (customer name, city) isn't recorded in the access log; only opening an order and the exports are.
- **Render**: check at deploy that the service is in the Frankfurt region (`region` in `render.yaml` applies only when the service is created) and that Render's data processing agreement is accepted.
- On the public pages, Render is listed as the hosting provider; if hosting changes, it changes there too (`src/legal.js`), with 30 days' notice to merchants.
