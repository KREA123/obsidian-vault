import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import { ProcessingError } from '../core/errors.js';
import { TrackingStatus } from './contract.js';

// "Curier de probă": behaves like a real courier without calling anyone. Used in demo
// mode and in "mod de probă", so the whole flow can be checked before going live.
// Reference implementation of the contract in ./contract.js.

const PROGRESSION = [
  TrackingStatus.CREATED,
  TrackingStatus.PICKED_UP,
  TrackingStatus.IN_TRANSIT,
  TrackingStatus.OUT_FOR_DELIVERY,
  TrackingStatus.DELIVERED,
];

export default {
  id: 'mock',
  name: 'Curier de probă',
  trackingUrl: (awb) => `https://example.com/tracking/${awb}`,
  credentialFields: [],
  settingsFields: [],

  async testConnection() {
    return { ok: true, message: 'Curierul de probă funcționează. Nu se trimite nimic real.' };
  },

  async createShipment(ctx, shipment) {
    if (!shipment.recipient.city) {
      throw new ProcessingError({
        code: 'ADDRESS_CITY_MISSING',
        message: 'Lipsește localitatea destinatarului.',
        hint: 'Completează localitatea în adresa de livrare.',
        field: 'shippingAddress.city',
        provider: 'mock',
      });
    }
    const awb = `TEST${Date.now().toString().slice(-8)}${Math.floor(Math.random() * 90 + 10)}`;
    const issued = ctx.cache?.get('mock:issued') || {};
    issued[awb] = { at: Date.now(), shipment };
    ctx.cache?.set('mock:issued', issued, 60 * 60 * 24 * 30);
    return { awb, price: 18.5 + Math.max(0, shipment.weightKg - 1) * 2 };
  },

  async getLabel(ctx, awb, { format = 'A6' } = {}) {
    const issued = ctx.cache?.get('mock:issued') || {};
    const s = issued[awb]?.shipment;
    const doc = await PDFDocument.create();
    const size = format === 'A4' ? [595, 842] : [298, 420];
    const page = doc.addPage(size);
    const font = await doc.embedFont(StandardFonts.Helvetica);
    const bold = await doc.embedFont(StandardFonts.HelveticaBold);
    const ascii = (t) => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\x20-\x7E]/g, '');
    let y = size[1] - 40;
    const line = (t, f = font, s2 = 11) => { page.drawText(ascii(t), { x: 24, y, size: s2, font: f, color: rgb(0, 0, 0) }); y -= s2 + 8; };
    line('ETICHETA DE PROBA - NU SE EXPEDIAZA', bold, 10);
    line(`AWB ${awb}`, bold, 20);
    if (s) {
      line(s.reference, bold, 14);
      line(s.recipient.name);
      line(s.recipient.street);
      line(`${s.recipient.city}, ${s.recipient.county} ${s.recipient.zip || ''}`);
      line(`Tel: ${s.recipient.phone}`);
      line(`Colete: ${s.parcels}  Greutate: ${s.weightKg} kg`);
      line(`Ramburs: ${s.cod ? `${s.cod.toFixed(2)} ${s.currency}` : '-'}`, bold, 14);
    }
    return Buffer.from(await doc.save());
  },

  async cancelShipment(ctx, awb) {
    const cancelled = ctx.cache?.get('mock:cancelled') || {};
    cancelled[awb] = true;
    ctx.cache?.set('mock:cancelled', cancelled, 60 * 60 * 24 * 30);
  },

  // Advances one step every few minutes so the tracking screen has something to show.
  async track(ctx, awbs) {
    const issued = ctx.cache?.get('mock:issued') || {};
    const cancelled = ctx.cache?.get('mock:cancelled') || {};
    const stepMs = Number(ctx.settings?.stepMinutes || 2) * 60_000;
    return awbs.map((awb) => {
      if (cancelled[awb]) return { awb, status: TrackingStatus.CANCELLED, statusText: 'AWB anulat' };
      const at = issued[awb]?.at ?? Date.now();
      const idx = Math.min(PROGRESSION.length - 1, Math.floor((Date.now() - at) / stepMs));
      const status = PROGRESSION[idx];
      return {
        awb,
        status,
        statusText: { created: 'AWB emis', picked_up: 'Ridicat de la expeditor', in_transit: 'În depozitul de destinație', out_for_delivery: 'Predat curierului pentru livrare', delivered: 'Livrat destinatarului' }[status],
        at: new Date().toISOString(),
        codCollected: status === TrackingStatus.DELIVERED,
      };
    });
  },
};
