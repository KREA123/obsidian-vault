// Single source of truth for every word in the Shopify App Store listing kit.
// build.mjs reads this file to render captions/alt text and to write LISTING-COPY.*.md,
// and fails the build if a field goes over its limit (see REQUIREMENTS.md for the sources).

export const LIMITS = {
  appName: 30,          // shopify.dev best practices: "30 characters or fewer"
  subtitle: 62,         // enforced by the Partner Dashboard form (not stated on shopify.dev; see REQUIREMENTS.md)
  introduction: 100,    // shopify.dev best practices
  details: 500,         // shopify.dev best practices
  feature: 80,          // shopify.dev best practices, per feature
  searchTerms: 5,       // shopify.dev best practices, max five terms
  integrations: 6,      // shopify.dev best practices, max six
};

export const COPY = {
  en: {
    appName: 'Expedo',
    appNameAlternatives: ['Expedo: AWB & Invoices', 'Expedo Shipping Romania'],
    subtitle: 'Ship orders in Romania without retyping AWBs and invoices',
    introduction: 'Catch bad addresses before the courier does, then ship many orders with AWB and invoice at once.',
    details:
      'Expedo takes each order from address check to collected cash on delivery. Before any AWB, it checks county, locality against the courier\'s list, Bucharest sector, phone and postal code, and suggests the right locality. It then creates the AWB at Cargus, Sameday, FAN Courier, GLS or DPD, issues the invoice in SmartBill, FGO or Oblio and marks the order fulfilled with tracking. Test mode runs it all on real orders, sending nothing. For stores shipping in Romania; interface in Romanian.',
    features: [
      'Address checked before the courier, with suggestions for misspelled localities',
      'AWB and invoice for many orders in one click, with every label in one PDF',
      'Orders marked fulfilled in Shopify with tracking, so customers get the email',
      'Parcels tracked; delivered cash-on-delivery orders marked collected and paid',
      'Rules choose courier, parcels or hold, e.g. easybox orders go to Sameday',
      'Test mode on real orders: test AWBs and invoices, nothing leaves the app',
      'Every error explained in Romanian, with what to do next',
      'One AWB and one invoice per order, even after a double click',
      'Temporary courier errors retried automatically, without blocking the order',
      'Picking list for the warehouse and cash-on-delivery export to CSV',
    ],
    // Add once the feature ships (it is being built now; don't list it before it is live):
    featuresPending: ['Warning when a customer has refused parcels before'],
    searchTerms: ['AWB', 'courier Romania', 'cash on delivery', 'invoicing', 'shipping labels'],
  },
  ro: {
    appName: 'Expedo',
    subtitle: 'Comenzi expediate fără să mai copiezi date în AWB și facturi',
    introduction: 'Prinzi adresele greșite înainte de curier și expediezi multe comenzi cu AWB și factură deodată.',
    details:
      'Expedo duce fiecare comandă de la verificarea adresei până la rambursul încasat. Înainte de AWB verifică județul, localitatea în nomenclatorul curierului, sectorul, telefonul și codul poștal și sugerează localitatea corectă. Apoi generează AWB-ul la Cargus, Sameday, FAN Courier, GLS sau DPD, emite factura în SmartBill, FGO sau Oblio și marchează comanda expediată, cu link de urmărire. Modul de probă rulează totul pe comenzi reale, fără să trimită nimic. Pentru livrări în România.',
    features: [
      'Adresa verificată înainte de curier, cu sugestii „Ai vrut: …?” pentru localitate',
      'AWB și factură pentru mai multe comenzi dintr-un clic, etichetele într-un PDF',
      'Comenzi marcate expediate în Shopify, cu AWB; clientul primește e-mailul',
      'Colete urmărite; la livrare, rambursul e marcat încasat și comanda plătită',
      'Reguli pentru curier, colete sau așteptare, ex. easybox → Sameday',
      'Mod de probă pe comenzi reale: AWB-uri și facturi de test, nu pleacă nimic',
      'Fiecare eroare explicată în română, cu ce ai de făcut',
      'Un singur AWB și o singură factură pe comandă, chiar dacă apeși de două ori',
      'Erorile temporare ale curierului se reîncearcă automat',
      'Listă de picking pentru depozit și export ramburs în CSV',
    ],
    featuresPending: ['Avertizare pentru clienții care au mai refuzat colete'],
    searchTerms: ['AWB', 'curier', 'ramburs', 'facturare', 'etichete AWB'],
  },
};

// Integrations field (max six). Couriers and invoicing apps Expedo connects to directly.
// Eight exist; pick six (recommended below, owner decides). Names only, no logos anywhere.
export const INTEGRATIONS = {
  all: ['Cargus', 'Sameday', 'FAN Courier', 'GLS', 'DPD', 'SmartBill', 'FGO', 'Oblio'],
  recommendedSix: ['Cargus', 'Sameday', 'FAN Courier', 'SmartBill', 'Oblio', 'FGO'],
};

// Desktop screenshots, 1600x900. `scene` names the capture in build.mjs.
export const SCREENSHOTS = [
  {
    id: '01-dashboard',
    scene: 'dashboard',
    en: { title: 'See what needs doing today', sub: 'Orders ready to ship, orders blocked by a problem, parcels on the way and cash on delivery still to collect.', alt: 'Expedo dashboard with orders to process, orders needing attention, parcels in transit and cash on delivery to collect' },
    ro: { title: 'Vezi dintr-o privire ce ai de făcut azi', sub: 'Comenzi de expediat, comenzi blocate de o problemă, colete pe drum și ramburs de încasat.', alt: 'Panoul Expedo cu comenzi de procesat, comenzi care necesită atenție, colete pe drum și ramburs de încasat' },
  },
  {
    id: '02-address-check',
    scene: 'address',
    en: { title: 'Fix the address before the courier rejects it', sub: 'The locality is checked against the courier\'s list. “Ai vrut: …?” (“Did you mean…?”) shows what to pick.', alt: 'Courier error for a misspelled locality with the suggestion Voluntari, and the delivery address corrected to Voluntari' },
    ro: { title: 'Adresa greșită, prinsă înainte de curier', sub: 'Localitatea e căutată în nomenclatorul curierului; vezi „Ai vrut: …?” și o corectezi direct în comandă.', alt: 'Eroare de curier pentru o localitate scrisă greșit, cu sugestia Voluntari, și adresa de livrare corectată' },
  },
  {
    id: '03-bulk-awb-invoice',
    scene: 'bulk',
    en: { title: 'AWB and invoice for many orders at once', sub: 'Select orders, click “Generează AWB + factură”, then print every label from one PDF.', alt: 'Order list with several orders selected and the Generate AWB plus invoice button, next to the labels PDF' },
    ro: { title: 'AWB și factură pentru mai multe comenzi deodată', sub: 'Selectezi comenzile, apeși „Generează AWB + factură”, apoi printezi toate etichetele dintr-un singur PDF.', alt: 'Lista de comenzi cu mai multe comenzi selectate și butonul Generează AWB + factură, lângă PDF-ul cu etichete' },
  },
  {
    id: '04-rules-test-mode',
    scene: 'rules',
    en: { title: 'Your rules, tried safely in test mode', sub: 'easybox orders go to Sameday, heavy orders get two parcels. Test mode runs on real orders and sends nothing.', alt: 'Rules screen with the easybox to Sameday rule, and the test mode and live mode switch' },
    ro: { title: 'Regulile tale, verificate în modul de probă', sub: 'Comenzile easybox merg la Sameday, cele grele în două colete. Modul de probă rulează pe comenzi reale și nu trimite nimic.', alt: 'Ecranul de reguli cu regula easybox către Sameday și comutatorul mod de probă / live' },
  },
  {
    id: '05-tracking-cod',
    scene: 'tracking',
    en: { title: 'Track every parcel until the cash is in', sub: 'Delivery status updates on its own. A delivered cash-on-delivery parcel is marked collected and the order paid.', alt: 'Order history timeline from AWB to delivery, with cash on delivery marked collected' },
    ro: { title: 'Urmărești coletul până încasezi rambursul', sub: 'Statusul se actualizează singur. La livrare, rambursul e marcat încasat și comanda plătită.', alt: 'Istoricul comenzii de la AWB până la livrare, cu rambursul marcat încasat' },
  },
  {
    id: '06-couriers-invoicing',
    scene: 'settings',
    en: { title: 'Connect your couriers and invoicing', sub: 'Cargus, Sameday, FAN Courier, GLS, DPD and SmartBill, FGO, Oblio. Test the connection before you go live.', alt: 'Settings with the five couriers and the three invoicing apps, each with its connection status' },
    ro: { title: 'Conectezi curierii și programul de facturare', sub: 'Cargus, Sameday, FAN Courier, GLS, DPD și SmartBill, FGO, Oblio. Testezi conexiunea înainte de live.', alt: 'Setări cu cei cinci curieri și cele trei programe de facturare, fiecare cu starea conexiunii' },
  },
];

// Mobile screenshots, 900x1600 (the UI is responsive). Different views from the desktop set.
export const MOBILE = [
  {
    id: 'm1-dashboard',
    scene: 'm-dash',
    en: { title: 'Today\'s orders, on your phone too', alt: 'Expedo dashboard on a phone with orders to process, orders needing attention and parcels on the way' },
    ro: { title: 'Comenzile de azi, și pe telefon', alt: 'Panoul Expedo pe telefon cu comenzi de procesat, comenzi care necesită atenție și colete pe drum' },
  },
  {
    id: 'm2-order',
    scene: 'm-order',
    en: { title: 'Fix an address from anywhere', alt: 'Order on a phone with the locality suggestion and the delivery address form' },
    ro: { title: 'Corectezi adresa de oriunde', alt: 'Comandă pe telefon cu sugestia de localitate și formularul adresei de livrare' },
  },
  {
    id: 'm3-delivered',
    scene: 'm-delivered',
    en: { title: 'Delivered and cash collected, at a glance', alt: 'Delivered order on a phone with AWB, tracking status and cash on delivery collected' },
    ro: { title: 'Livrat și încasat, dintr-o privire', alt: 'Comandă livrată pe telefon cu AWB, status de urmărire și ramburs încasat' },
  },
];

export const FEATURE = {
  en: { title: 'From order to AWB, invoice and collected cash', sub: 'For online stores shipping in Romania', alt: 'Expedo order list with orders selected for AWB and invoice, and an order marked delivered with cash collected' },
  ro: { title: 'De la comandă la AWB, factură și ramburs încasat', sub: 'Pentru magazinele online care livrează în România', alt: 'Lista de comenzi Expedo cu comenzi selectate pentru AWB și factură și o comandă livrată cu rambursul încasat' },
};
