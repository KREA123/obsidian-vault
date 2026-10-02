// Contract every courier adapter implements. Documentation only (JSDoc), plus the
// normalized tracking statuses all adapters must map to.
//
// An adapter module default-exports an object:
//
// {
//   id: 'cargus',                       // stable key, lowercase
//   name: 'Cargus',                     // display name
//   trackingUrl: (awb) => string,       // public tracking page for the customer
//   credentialFields: Field[],          // secrets, stored encrypted (user, password, API key...)
//   settingsFields: Field[],            // non-secret options (pickup point, service, defaults...)
//
//   async testConnection(ctx) -> { ok: true, message: string, info?: object }
//       Must throw ProcessingError (code AUTH_FAILED) on bad credentials.
//
//   async createShipment(ctx, shipment) -> { awb: string, price?: number, raw?: any }
//       Must throw ProcessingError with a merchant-readable message when the courier refuses;
//       for address problems use code 'ADDRESS_*' and set `field`.
//
//   async getLabel(ctx, awb, { format }) -> Buffer   // PDF bytes; format 'A4' | 'A6'
//   async cancelShipment(ctx, awb) -> void
//   async track(ctx, awbs: string[]) -> TrackingResult[]   // batch; missing AWBs simply omitted
//
//   // optional
//   async listPickupPoints(ctx) -> [{ id, name, address }]   // sender locations / puncte de ridicare
//   async listServices(ctx) -> [{ id, name }]
//   async listLockers(ctx, { county, city }) -> [{ id, name, address }]
// }
//
// Field: { key, label, type: 'text'|'password'|'number'|'select'|'checkbox', required?, help?, options?: [{value,label}], default? }
//
// ctx: {
//   credentials: object,   // values for credentialFields
//   settings: object,      // values for settingsFields
//   http: request,         // src/lib/http.js request(provider, url, opts) — use this, not fetch
//   cache: { get(key), set(key, value, ttlSeconds) },   // per-store cache (tokens, nomenclators)
//   log: (message, data?) => void,
// }
//
// Shipment (built by the pipeline from a Shopify order, already validated & normalized):
// {
//   reference: '#1024',                 // order name, goes on the AWB as client reference
//   recipient: {
//     name: string, contactPerson: string, phone: '07xxxxxxxx', email?: string,
//     county: 'Cluj',                   // canonical county name (no diacritics issues — see core/address.js)
//     countyCode: 'CJ',
//     city: 'Cluj-Napoca',
//     sector?: 3,                       // București only
//     street: string,                   // address1 (+ address2)
//     zip?: '400001',
//     country: 'RO',
//     company?: string,
//   },
//   parcels: 1,                         // number of packages
//   weightKg: 1.2,                      // total weight, >= 0.1
//   envelopes: 0,
//   dimensionsCm?: { length, width, height },
//   cod: 149.9,                         // ramburs amount, 0 when prepaid
//   currency: 'RON',
//   declaredValue: 0,                   // asigurare; 0 = none
//   contents: 'Jucării',                // conținut
//   notes?: string,                     // observații pentru curier
//   service?: string,                   // adapter-specific service id override (from rules)
//   lockerId?: string,                  // easybox / FANbox / Ship&Go point when delivering to a locker
//   openPackage?: boolean,              // deschidere colet la livrare
//   saturday?: boolean,
// }
//
// TrackingResult: { awb, status: TrackingStatus, statusText: string, at?: ISOString, codCollected?: boolean }

/** Normalized tracking statuses. Adapters map every courier-specific status to one of these. */
export const TrackingStatus = Object.freeze({
  CREATED: 'created',            // AWB emis, coletul nu a fost încă ridicat
  PICKED_UP: 'picked_up',        // ridicat de curier
  IN_TRANSIT: 'in_transit',      // în tranzit / în depozit
  OUT_FOR_DELIVERY: 'out_for_delivery',
  DELIVERED: 'delivered',        // livrat (ramburs încasat de curier, dacă era)
  FAILED_ATTEMPT: 'failed_attempt', // destinatar absent, adresă greșită, amânat
  RETURNING: 'returning',        // refuzat / în retur
  RETURNED: 'returned',          // returnat la expeditor
  CANCELLED: 'cancelled',
  UNKNOWN: 'unknown',
});

export const FINAL_STATUSES = new Set([TrackingStatus.DELIVERED, TrackingStatus.RETURNED, TrackingStatus.CANCELLED]);

// Status labels: tracking.<status> in the catalogs (src/i18n).
