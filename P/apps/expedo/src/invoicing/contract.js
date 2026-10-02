// Contract every invoicing adapter implements. Documentation only (JSDoc).
//
// An adapter module default-exports an object:
//
// {
//   id: 'smartbill',
//   name: 'SmartBill',
//   credentialFields: Field[],          // same Field shape as couriers/contract.js
//   settingsFields: Field[],            // series, VAT payer, send e-mail, warehouse...
//
//   async testConnection(ctx) -> { ok: true, message: string, info?: object }
//       Must throw ProcessingError (code AUTH_FAILED) on bad credentials.
//
//   async createInvoice(ctx, invoice) -> { series: string, number: string, url?: string, raw?: any }
//   async getPdf(ctx, { series, number }) -> Buffer
//   async cancelInvoice(ctx, { series, number }) -> void      // anulare (if allowed) — never deletes
//   async stornoInvoice(ctx, { series, number }) -> { series, number }   // optional: factură de stornare
//   async registerPayment(ctx, { series, number, amount, date, method, reference }) -> void  // optional: încasare (ramburs livrat)
//
//   // optional
//   async listSeries(ctx) -> [{ id, name }]
// }
//
// ctx is the same shape as for couriers: { credentials, settings, http, cache, log }.
//
// Invoice (built by the pipeline from the Shopify order; amounts are what the customer paid):
// {
//   reference: '#1024',
//   issueDate: '2026-10-02',            // YYYY-MM-DD, Europe/Bucharest
//   dueDate: '2026-10-02',
//   currency: 'RON',
//   language: 'RO',
//   client: {
//     name: string,                     // company name for B2B, person name for B2C
//     isCompany: boolean,
//     vatCode?: string,                 // CUI / CIF, e.g. 'RO12345678' (only for companies)
//     regCom?: string,                  // J12/123/2020
//     address: string, city: string, county: string, countyCode: string, zip?: string, country: 'Romania',
//     email?: string, phone?: string,
//   },
//   lines: [{
//     name: string, code?: string,      // product title (+ variant), SKU
//     quantity: number,
//     unitPrice: number,                // GROSS unit price incl. VAT, after line discounts, up to 4 decimals
//     vatRate: number,                  // 21, 11, 0 ...
//     unit: 'buc',
//     isShipping?: boolean,             // the shipping cost line ('Transport')
//   }],
//   total: number,                      // gross total, should equal sum(lines) within 0.05
//   paid: boolean,                      // already paid online (card) — adapters may mark the invoice as collected
//   paymentMethod: 'card'|'cod'|'transfer'|'other',
//   mentions?: string,                  // e.g. 'Comanda #1024'
//   sendEmail?: boolean,
//   idempotencyKey: string,             // '#1024', or '#1024-2' when re-invoicing after a storno; use for provider duplicate checks
// }
//
// Prices are sent VAT-inclusive (prețuri cu TVA inclus) — that's how Shopify stores sell to
// consumers; adapters must use the provider's "price includes VAT" flag, not recompute.
// If the merchant is not a VAT payer (settings.vatPayer === false), adapters send 0% / "neplătitor".
