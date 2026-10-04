// Single source of truth for every word in the Shopify App Store listing kit (English listing).
// build.mjs reads this file to render captions/alt text and to write LISTING-COPY.md, and fails the
// build if a field goes over its limit (sources in REQUIREMENTS.md). The v1 Romanian texts are in
// ro-archive/copy.v1-en-ro.mjs (not used by the build).

export const LIMITS = {
  appName: 30,          // shopify.dev best practices: "30 characters or fewer"
  subtitle: 62,         // enforced by the Partner Dashboard form (not stated on shopify.dev; see REQUIREMENTS.md)
  introduction: 100,    // shopify.dev best practices
  details: 500,         // shopify.dev best practices
  feature: 80,          // shopify.dev best practices, per feature
  searchTerms: 5,       // shopify.dev best practices, max five terms
  integrations: 6,      // shopify.dev best practices, max six
  publicPlans: 8,       // shopify.dev Shopify App Pricing: up to eight public plans
  // Plan "Display name" / "Top features": shopify.dev states no character limit. We hold them to the
  // listing's own feature limit (80 per line) and short names; the form's counters are authoritative.
  planName: 20,
  planFeature: 80,
};

export const COPY = {
  appName: 'Expedo',
  appNameAlternatives: ['Expedo: AWB & Invoices', 'Expedo Shipping Romania'],
  subtitle: 'Ship orders in Romania without retyping AWBs and invoices',
  introduction: 'Catch bad addresses before the courier does, then ship many orders with AWB and invoice at once.',
  details:
    'Expedo takes each order from address check to collected cash on delivery. Before any AWB, it checks county, locality against the courier\'s list, Bucharest sector, phone and postal code, and suggests the right locality. It then creates the AWB at Cargus, Sameday, FAN Courier, GLS or DPD, issues the invoice in SmartBill, FGO or Oblio and marks the order fulfilled with tracking. Test mode runs it all on real orders, sending nothing. For stores shipping in Romania. English and Romanian interface.',
  features: [
    'Address checked before the courier, with suggestions for misspelled localities',
    'Warning when a customer has refused parcels before, before you create the AWB',
    'AWB and invoice for many orders in one click, with every label in one PDF',
    'Orders marked fulfilled in Shopify with tracking, so customers get the email',
    'Parcels tracked; delivered cash-on-delivery orders marked collected and paid',
    'Rules choose courier, parcels or hold, e.g. easybox orders go to Sameday',
    'Test mode on real orders: test AWBs and invoices, nothing leaves the app',
    'Every error explained in plain words, with what to do next',
    'One AWB and one invoice per order, even after a double click',
    'Temporary courier errors retried automatically, without blocking the order',
    'Picking list for the warehouse and cash-on-delivery export to CSV',
  ],
  searchTerms: ['AWB', 'courier Romania', 'cash on delivery', 'invoicing', 'shipping labels'],
  // The app UI is usable in both (req. 4.3.2).
  languages: ['English', 'Romanian'],
};

// Pricing: Shopify App Pricing (managed pricing), USD, billed every 30 days. No free plan: every plan has a
// 5-day free trial. Prices appear ONLY here and in the Pricing section of the form, never in images (req. 4.2).
export const PRICING = {
  billing: 'Recurring charge, Shopify App Pricing (no free plan)',
  currency: 'USD',
  interval: 'every 30 days',
  trialDays: 5,
  // Top features: the English text from P/apps/expedo/PRICING.md section 2.
  plans: [
    { name: 'Pro', handle: 'pro', price: 15, features: ['Up to 1,000 orders every 30 days', 'All couriers and invoicing apps', 'Address & phone check', 'Test mode', 'Bulk processing and rules', 'Tracking and COD reconciliation'] },
    { name: 'Pro Max', handle: 'pro_max', price: 30, features: ['Unlimited orders', 'Everything in Pro', 'Automatic processing of new orders', 'Customer refusal history', 'COD export (CSV)', 'Multiple stores', 'Priority support'] },
  ],
  // "Description of additional charges" / notes: none. What counts toward the limit (PRICING.md §4):
  note: 'Orders = orders that get a live AWB in the billing period; test-mode AWBs never count and a canceled AWB frees its slot.',
};

// Integrations field (max six). Couriers and invoicing apps Expedo connects to directly.
export const INTEGRATIONS = {
  all: ['Cargus', 'Sameday', 'FAN Courier', 'GLS', 'DPD', 'SmartBill', 'FGO', 'Oblio'],
  recommendedSix: ['Cargus', 'Sameday', 'FAN Courier', 'SmartBill', 'Oblio', 'FGO'],
};

// Desktop screenshots, 1600x900. `scene` names the capture in build.mjs.
export const SCREENSHOTS = [
  {
    id: '01-dashboard',
    scene: 'dashboard',
    title: 'See what needs doing today',
    sub: 'Orders ready to ship, orders blocked by a problem, parcels on the way and cash on delivery still to collect.',
    alt: 'Expedo dashboard with orders to process, orders needing attention, parcels in transit and cash on delivery to collect',
  },
  {
    id: '02-address-check',
    scene: 'address',
    title: 'Fix the address before the courier rejects it',
    sub: 'The locality is checked against the courier\'s list, and “Did you mean…?” shows what to pick.',
    alt: 'Courier error for a misspelled locality with the suggestion Voluntari, and the shipping address corrected to Voluntari',
  },
  {
    id: '03-bulk-awb-invoice',
    scene: 'bulk',
    title: 'AWB and invoice for many orders at once',
    sub: 'Select orders, click “Create AWB + invoice”, print every label from one PDF. Past refusals are flagged.',
    alt: 'Order list with several orders selected, the Create AWB plus invoice button, a refused-parcels warning, and the labels PDF',
  },
  {
    id: '04-rules-test-mode',
    scene: 'rules',
    title: 'Your rules, tried safely in test mode',
    sub: 'easybox orders go to Sameday, heavy orders get two parcels. Test mode runs on real orders and sends nothing.',
    alt: 'Rules screen with the easybox to Sameday rule, and the test mode and live mode switch',
  },
  {
    id: '05-tracking-cod',
    scene: 'tracking',
    title: 'Track every parcel until the cash is in',
    sub: 'Delivery status updates on its own. A delivered cash-on-delivery parcel is marked collected and the order paid.',
    alt: 'Order history timeline from AWB to delivery, with cash on delivery marked collected',
  },
  {
    id: '06-couriers-invoicing',
    scene: 'settings',
    title: 'Connect your couriers and invoicing',
    sub: 'Cargus, Sameday, FAN Courier, GLS, DPD and SmartBill, FGO, Oblio. Test the connection before you go live.',
    alt: 'Settings with the five couriers and the three invoicing apps, each with its connection status',
  },
];

// Mobile screenshots, 900x1600 (the UI is responsive). Different views from the desktop set.
export const MOBILE = [
  { id: 'm1-dashboard', scene: 'm-dash', title: 'Today\'s orders, on your phone too', alt: 'Expedo dashboard on a phone with orders to process, orders needing attention and parcels on the way' },
  { id: 'm2-refused', scene: 'm-refused', title: 'Know who refused parcels before', alt: 'Order on a phone with a warning that the customer refused one parcel before, and the customer history' },
  { id: 'm3-delivered', scene: 'm-delivered', title: 'Delivered and cash collected, at a glance', alt: 'Delivered order on a phone with AWB, tracking status and cash on delivery collected' },
];

export const FEATURE = {
  title: 'From order to AWB, invoice and collected cash',
  sub: 'For online stores shipping in Romania',
  alt: 'Expedo order with its AWB, invoice, delivered status and cash on delivery collected',
};
