# Pricing — what to set up in the Partner Dashboard

Expedo is billed through **Shopify App Pricing**, Shopify's hosted billing. Until May 2026 it was called "Managed Pricing". The plans live in the Partner Dashboard; Shopify hosts the page where merchants pick a plan and handles the charges, trials, proration and test charges. The app never creates charges itself. It reads which plan the store is on and applies that plan's limits ([`src/core/plans.js`](src/core/plans.js)).

## 1. Turn on Shopify App Pricing

Partner Dashboard → **Apps** → Expedo → **Distribution** → beside "Shopify App Store listing", **Manage listing** → under "Published languages", **Edit** (English) → **Pricing content** → **Manage** → **Settings**:

- **Pricing method:** Shopify App Pricing
- **Default billing frequency:** Monthly (every 30 days)

## 2. The two plans

There is **no free plan**. Create two **public** plans, each with a **5-day free trial**. **The display name has to be exactly the name in the table** (upper or lower case doesn't matter). The app finds the plan by its name or handle: "Pro Max", "pro_max", "promax" and "Expedo Pro Max" all mean Pro Max; "Pro" and "Expedo Pro" mean Pro. If an older Free / Starter / Growth / Plus plan exists from earlier setups, unpublish it (the app still maps those names: Starter → Pro, Growth / Plus → Pro Max, Free → no plan).

| Display name | Handle | Price (USD) | Billing | Free trial | Orders |
|---|---|---|---|---|---|
| **Pro** | `pro` | $15 | every 30 days | 5 days | up to 1,000 per billing period |
| **Pro Max** | `pro_max` | $30 | every 30 days | 5 days | unlimited |

For each plan:

- **Free trial:** 5 days.
- **Welcome link:** `/`. Shopify adds `?plan_handle=…`, and the app then checks the new plan with Shopify straight away.
- **Free for partners and developers:** on. This lets reviewers and other partners test without being charged.
- **Top features:** add them in English and in Romanian. Shopify only shows a plan to merchants whose language has a description. Text to paste:

| Plan | English | Romanian |
|---|---|---|
| Pro | Up to 1,000 orders every 30 days · All couriers and invoicing apps · Address & phone check · Test mode · Bulk processing and rules · Tracking and COD reconciliation | Până la 1.000 de comenzi la 30 de zile · Toți curierii și aplicațiile de facturare · Verificarea adresei și a telefonului · Mod de probă · Procesare în bloc și reguli · Urmărirea coletelor și reconcilierea rambursurilor |
| Pro Max | Unlimited orders · Everything in Pro · Automatic processing of new orders · Customer refusal history · COD export (CSV) · Multiple stores · Priority support | Comenzi nelimitate · Tot ce e în Pro · Procesarea automată a comenzilor noi · Istoricul refuzurilor clientului · Export rambursuri (CSV) · Mai multe magazine · Suport prioritar |

## 3. Let the app read the plan (Partner API)

For apps that set up App Pricing after April 2026, Shopify reports the plan **only through the Partner API** (Active Subscription API). Webhooks and `charge_id` are no longer used. The app therefore needs:

1. Partner Dashboard → **Settings** → **Partner API clients** → **Manage Partner API clients**: create a client with the **Manage apps** permission. Only the organization owner can do this.
2. Set these server variables (see `.env.example` and `render.yaml`):
   - `SHOPIFY_PARTNER_API_TOKEN`: the client's access token
   - `SHOPIFY_PARTNER_ORG_ID`: the number in the Partner Dashboard URL
   - `SHOPIFY_APP_GID`: `gid://shopify/App/<number in the app's Partner Dashboard URL>`
   - `SHOPIFY_APP_HANDLE`: the app handle (`handle` in `shopify.app.toml`, `expedo` by default). It's part of the plan page URL `https://admin.shopify.com/store/{store}/charges/{app_handle}/pricing_plans`.

Without the Partner API variables, the app falls back to the Admin API (`currentAppInstallation.activeSubscriptions`). That only works for Billing API subscriptions and for managed pricing set up before April 2026. With neither source available, no store has an active plan (live AWBs and invoices are refused; test mode works).

The app also subscribes to the `app_subscriptions/update` webhook (`shopify.app.toml`). Shopify still sends it for Billing API subscriptions, but App Pricing stopped sending it on April 28, 2026. When it arrives, the app re-checks the plan right away; otherwise the regular checks below catch the change.

## 4. What the app does with each plan

| | No plan | Pro | Pro Max |
|---|---|---|---|
| Live AWBs and invoices | — (refused: choose a plan) | up to 1,000 orders per billing period | unlimited |
| Test mode (every feature, test providers) | ✓ | ✓ | ✓ |
| Address & phone check, all couriers and invoicing apps | ✓ | ✓ | ✓ |
| Bulk processing, rules, tracking, COD reconciliation (marked collected on delivery) | ✓ | ✓ | ✓ |
| Automatic processing of new orders | — | — | ✓ |
| Customer refusal history (warning, "Parcels refused before" rule field, history on the order) | — | — | ✓ |
| COD export (CSV) | — | — | ✓ |
| Multiple stores (a flag only in the app) | — | — | ✓ |
| Priority support | — | — | ✓ |

- **No plan** means no active subscription: the merchant never chose one, canceled during the trial, or the subscription expired or was frozen. A new live AWB or invoice is refused with "Choose a plan to start shipping — every plan starts with a 5-day free trial" (`PLAN_REQUIRED`) and a hint pointing to Settings → Plan. Test mode works fully. Tracking, labels, canceling AWBs, reversing invoices and fulfilling orders that already have their documents are never blocked. A banner "Choose a plan — 5-day free trial" with a **Change plan** link stays at the top of the dashboard until a plan is active.
- **What counts on Pro:** orders whose AWB was created in **live** mode during the current billing period. That is the subscription's 30-day period (including the trial), or the calendar month (Bucharest time) when there's no period. AWBs made in test mode never count. A canceled AWB frees its slot.
- **At the Pro limit:** a new live AWB is refused with "You've reached the Pro plan's limit of 1,000 orders this month" (`PLAN_LIMIT_REACHED`) and a hint to upgrade to Pro Max. Tracking, labels, canceling AWBs, reversing invoices, invoices and fulfillment for orders that already have an AWB, and test mode keep working.
- **From 80% of the limit:** a banner at the top shows the usage and a "Change plan" link.
- **Pro Max features** are shown disabled on Pro and without a plan, with "Available on Pro Max", and never cause errors. A saved "automatic processing" setting is kept and starts working again after an upgrade. Rules that use "Parcels refused before" are skipped.
- **Settings → Plan** shows the current plan (or "No plan yet"), the usage on Pro (e.g. "812 / 1,000 orders this month"), the trial days left, both plans side by side with price, limit and features (the current one highlighted), and **Choose a plan** / **Change plan**, which opens Shopify's plan page outside the app frame.
- **When the plan is checked:** on install, when the merchant comes back from the plan page, after the webhook, with "Check again" in Settings → Plan, and otherwise at most every 6 hours (worker job `refresh_plan`). If Shopify can't be reached, the last known plan stays, so a paying store is never downgraded because of an outage. An active subscription whose name the app doesn't recognize counts as Pro (logged as a warning), so a paying store is never locked out.
- **Older cached plans:** stores saved with an old plan id are mapped: Growth / Plus → Pro Max, Starter → Pro, Free → no plan.
- **Always on Pro Max:** the demo store and the stores in `SHOPIFY_OWN_STORES`. Shopify is never asked about them, and they never see the "Choose a plan" banner.

## 5. Testing

On a development store in the same Partner organization, every plan can be selected at no charge. Shopify creates the subscription with an effective price of $0, and it counts as active. Test both plans, then open **Settings → Plan** in the app and check the plan name, the limit and the 5-day trial. To see the no-plan state, cancel the subscription: the "Choose a plan" banner appears and live AWBs are refused, while test mode keeps working.
