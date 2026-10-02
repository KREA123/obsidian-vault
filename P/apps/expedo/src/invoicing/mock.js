import { PDFDocument, StandardFonts } from 'pdf-lib';
import { m, t } from '../i18n/index.js';

// Test invoicing: numbers invoices locally, calls nobody. Demo mode and test mode
// use it so a real series is never consumed by a test (no test invoices on real orders).

export default {
  id: 'mock',
  name: 'Test invoicing',
  credentialFields: [],
  settingsFields: [{ key: 'series', type: 'text', default: 'TEST' }],

  async testConnection() {
    return { ok: true, message: m('mock.invoicer.connected') };
  },

  async createInvoice(ctx, invoice) {
    const series = ctx.settings?.series || 'TEST';
    const next = (ctx.cache?.get(`mock:inv:${series}`) || 0) + 1;
    ctx.cache?.set(`mock:inv:${series}`, next, 60 * 60 * 24 * 365);
    const all = ctx.cache?.get('mock:invoices') || {};
    all[`${series}-${next}`] = invoice;
    ctx.cache?.set('mock:invoices', all, 60 * 60 * 24 * 365);
    return { series, number: String(next).padStart(4, '0') };
  },

  async getPdf(ctx, { series, number }) {
    const inv = (ctx.cache?.get('mock:invoices') || {})[`${series}-${Number(number)}`];
    const doc = await PDFDocument.create();
    const page = doc.addPage([595, 842]);
    const font = await doc.embedFont(StandardFonts.Helvetica);
    const ascii = (t) => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\x20-\x7E]/g, '');
    let y = 790;
    const line = (t, size = 11) => { page.drawText(ascii(t), { x: 48, y, size, font }); y -= size + 8; };
    // Text in the store's language (ctx.locale, set by the pipeline).
    const L = ctx.locale || 'en';
    line(t(L, 'mock.invoice.title', { series, number }), 18);
    line(t(L, 'mock.invoice.noValue'), 9);
    if (inv) {
      line(t(L, 'mock.invoice.client', { name: `${inv.client.name}${inv.client.vatCode ? ` (${inv.client.vatCode})` : ''}` }));
      line(`${inv.client.address}, ${inv.client.city}, ${inv.client.county}`);
      y -= 10;
      for (const l of inv.lines) line(t(L, 'mock.invoice.line', { quantity: l.quantity, name: l.name, price: l.unitPrice.toFixed(2), vat: l.vatRate }), 10);
      y -= 10;
      line(t(L, 'mock.invoice.total', { total: inv.total.toFixed(2), currency: inv.currency }), 14);
    }
    return Buffer.from(await doc.save());
  },

  async cancelInvoice() {},

  async stornoInvoice(ctx, { series }) {
    const next = (ctx.cache?.get(`mock:inv:${series}`) || 0) + 1;
    ctx.cache?.set(`mock:inv:${series}`, next, 60 * 60 * 24 * 365);
    return { series, number: String(next).padStart(4, '0') };
  },

  async registerPayment() {},
};
