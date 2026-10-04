# Pricing — what to set up in the Partner Dashboard

Expedo is billed through **Shopify App Pricing**, Shopify's hosted billing. Until May 2026 it was called "Managed Pricing". The plans live in the Partner Dashboard; Shopify hosts the page where merchants pick a plan and handles the charges, trials, proration and test charges. The app never creates charges itself. It reads which plan the store is on and applies that plan's limits ([`src/core/plans.js`](src/core/plans.js)).

## 1. Turn on Shopify App Pricing

Partner Dashboard → **Apps** → Expedo → **Distribution** → beside "Shopify App Store listing", **Manage listing** → under "Published languages", **Edit** (English) → **Pricing content** → **Manage** → **Settings**:

- **Pricing method:** Shopify App Pricing
- **Default billing frequency:** Monthly (every 30 days)

## 2. The four plans

Create four **public** plans. **The display name has to be exactly the name in the table** (upper or lower case doesn't matter). The app finds the plan by its name or handle, so "Starter" and `starter` both work. A name it doesn't recognize counts as Free.

| Display name | Handle | Price (USD, every 30 days) | Free trial | Orders / month |
|---|---|---|---|---|
| **Free** | `free` | $0 | — (it's free) | 50 |
| **Starter** | `starter` | $14.99 | 30 days | 1,000 |
| **Growth** | `growth` | $24.99 | 30 days | unlimited |
| **Plus** | `plus` | $49.99 | 30 days | unlimited |

For each plan:

- **Welcome link:** `/`. Shopify adds `?plan_handle=…`, and the app then checks the new plan with Shopify straight away.
- **Free for partners and developers:** on, for every paid plan. This lets reviewers and other partners test without being charged.
- **Top features:** add them in English and in Romanian. Shopify only shows a plan to merchants whose language has a description. Suggested text:

| Plan | English | Romanian |
|---|---|---|
| Free | Up to 50 orders a month · All couriers and invoicing apps · Address & phone check · Test mode | Până la 50 de comenzi pe lună · Toți curierii și aplicațiile de facturare · Verificarea adresei și a telefonului · Mod de probă |
| Starter | Up to 1,000 orders a month · Address & phone check · Bulk processing and rules · Tracking and COD reconciliation | Până la 1.000 de comenzi pe lună · Verificarea adresei și a telefonului · Procesare în bloc și reguli · Urmărirea coletelor și reconcilierea rambursurilor |
| Growth | Unlimited orders · Automatic processing of new orders · Customer refusal history · COD export (CSV) · Priority support | Comenzi nelimitate · Procesarea automată a comenzilor noi · Istoricul refuzurilor clientului · Export rambursuri (CSV) · Suport prioritar |
| Plus | Everything in Growth · Multiple stores under one account · One custom integration, set up by us | Tot ce e în Growth · Mai multe magazine într-un singur cont · O integrare personalizată, făcută de noi |

Shopify allows at most eight public plans and only one free public plan.

## 3. Let the app read the plan (Partner API)

For apps that set up App Pricing after April 2026, Shopify reports the plan **only through the Partner API** (Active Subscription API). Webhooks and `charge_id` are no longer used. The app therefore needs:

1. Partner Dashboard → **Settings** → **Partner API clients** → **Manage Partner API clients**: create a client with the **Manage apps** permission. Only the organization owner can do this.
2. Set these server variables (see `.env.example` and `render.yaml`):
   - `SHOPIFY_PARTNER_API_TOKEN`: the client's access token
   - `SHOPIFY_PARTNER_ORG_ID`: the number in the Partner Dashboard URL
   - `SHOPIFY_APP_GID`: `gid://shopify/App/<number in the app's Partner Dashboard URL>`
   - `SHOPIFY_APP_HANDLE`: the app handle (`handle` in `shopify.app.toml`, `expedo` by default). It's part of the plan page URL `https://admin.shopify.com/store/{store}/charges/{app_handle}/pricing_plans`.

Without the Partner API variables, the app falls back to the Admin API (`currentAppInstallation.activeSubscriptions`). That only works for Billing API subscriptions and for managed pricing set up before April 2026. With neither source available, every store is treated as Free.

The app also subscribes to the `app_subscriptions/update` webhook (`shopify.app.toml`). Shopify still sends it for Billing API subscriptions, but App Pricing stopped sending it on April 28, 2026. When it arrives, the app re-checks the plan right away; otherwise the regular checks below catch the change.

## 4. What the app does with each plan

| | Free | Starter | Growth | Plus |
|---|---|---|---|---|
| Orders with a live AWB per billing period | 50 | 1,000 | unlimited | unlimited |
| Address & phone check, all couriers and invoicing apps, test mode | ✓ | ✓ | ✓ | ✓ |
| Bulk processing, rules, tracking, COD reconciliation (marked collected on delivery) | ✓ | ✓ | ✓ | ✓ |
| Automatic processing of new orders | — | — | ✓ | ✓ |
| Customer refusal history (warning, "Parcels refused before" rule field, history on the order) | — | — | ✓ | ✓ |
| COD export (CSV) | — | — | ✓ | ✓ |
| Priority support | — | — | ✓ | ✓ |
| Multiple stores, one custom integration (handled by us; a flag only in the app) | — | — | — | ✓ |

- **What counts:** orders whose AWB was created in **live** mode during the current billing period. That is the subscription's 30-day period (including the trial), or the calendar month (Bucharest time) when there's no paid period, for example on Free. AWBs made in test mode never count. A canceled AWB frees its slot.
- **At the limit:** a new live AWB is refused with "You've reached the Free plan's limit of 50 orders this month" and a hint to upgrade. Tracking, labels, canceling AWBs, reversing invoices, invoices and fulfillment for orders that already have an AWB, and test mode keep working.
- **From 80% of the limit:** a banner at the top shows the usage and a "Change plan" button.
- **Features on a higher plan** are shown disabled, with "Available on Growth", and never cause errors. A saved "automatic processing" setting is kept and starts working again after an upgrade. Rules that use "Parcels refused before" are skipped.
- **Settings → Plan** shows the plan, usage (e.g. "37 / 50 orders this month"), the trial days left, and **Change plan**, which opens Shopify's plan page outside the app frame.
- **When the plan is checked:** on install, when the merchant comes back from the plan page, after the webhook, with "Check again" in Settings → Plan, and otherwise at most every 6 hours (worker job `refresh_plan`). If Shopify can't be reached, the last known plan stays, so a paying store is never downgraded because of an outage.
- **Always on Plus:** the demo store and the stores in `SHOPIFY_OWN_STORES`. Shopify is never asked about them.

## 5. Testing

On a development store in the same Partner organization, every plan can be selected at no charge. Shopify creates the subscription with an effective price of $0, and it counts as active. Test the four plans, then open **Settings → Plan** in the app and check the plan name, the limit and the trial.
