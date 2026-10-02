import { PDFDocument, StandardFonts } from 'pdf-lib';

// "Facturare de probă": numbers invoices locally, calls nobody. Demo mode and "mod de probă"
// use it so a real series is never consumed by a test (no test invoices on real orders).

export default {
  id: 'mock',
  name: 'Facturare de probă',
  credentialFields: [],
  settingsFields: [{ key: 'series', label: 'Serie', type: 'text', default: 'TEST' }],

  async testConnection() {
    return { ok: true, message: 'Facturarea de probă funcționează. Nu se emite nicio factură reală.' };
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
    line(`FACTURA DE PROBA ${series} ${number}`, 18);
    line('Document fara valoare fiscala.', 9);
    if (inv) {
      line(`Client: ${inv.client.name}${inv.client.vatCode ? ` (${inv.client.vatCode})` : ''}`);
      line(`${inv.client.address}, ${inv.client.city}, ${inv.client.county}`);
      y -= 10;
      for (const l of inv.lines) line(`${l.quantity} x ${l.name}  @ ${l.unitPrice.toFixed(2)}  TVA ${l.vatRate}%`, 10);
      y -= 10;
      line(`Total: ${inv.total.toFixed(2)} ${inv.currency}`, 14);
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
