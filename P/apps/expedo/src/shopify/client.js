import { config } from '../config.js';
import { request } from '../lib/http.js';
import { ProcessingError } from '../core/errors.js';
import * as Q from './queries.js';
import { mapOrder } from './mapper.js';

// Admin GraphQL client for one store. Demo stores have no token and never reach this.

export function shopifyClient(store) {
  async function gql(query, variables = {}) {
    if (!store.accessToken) {
      throw new ProcessingError({ code: 'SHOPIFY_NOT_CONNECTED', message: 'Magazinul nu e conectat la Shopify.', hint: 'Reinstalează aplicația din Shopify.', provider: 'shopify' });
    }
    const url = `https://${store.shop}/admin/api/${config.shopify.apiVersion}/graphql.json`;
    for (let attempt = 0; ; attempt++) {
      const { body } = await request('Shopify', url, {
        method: 'POST',
        headers: { 'X-Shopify-Access-Token': store.accessToken },
        json: { query, variables },
      });
      const throttled = body?.errors?.some?.((e) => e?.extensions?.code === 'THROTTLED');
      if (throttled && attempt < 3) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      if (body?.errors?.length) {
        throw new ProcessingError({
          code: 'SHOPIFY_GRAPHQL',
          message: `Shopify a refuzat cererea: ${body.errors.map((e) => e.message).join('; ')}`,
          hint: 'Dacă scrie de permisiuni (access denied), reinstalează aplicația ca să accepți permisiunile noi.',
          retryable: throttled,
          provider: 'shopify',
          details: body.errors,
        });
      }
      return body.data;
    }
  }

  function userErrors(result, what) {
    const errs = result?.userErrors || [];
    if (errs.length) {
      throw new ProcessingError({
        code: 'SHOPIFY_USER_ERROR',
        message: `Shopify nu a acceptat ${what}: ${errs.map((e) => e.message).join('; ')}`,
        hint: 'Verifică comanda în Shopify (poate a fost deja expediată, anulată sau editată).',
        provider: 'shopify',
        details: errs,
      });
    }
    return result;
  }

  return {
    gql,

    async shopInfo() {
      return (await gql(Q.SHOP_QUERY)).shop;
    },

    /** Fetches orders newest first. `search` uses Shopify search syntax, e.g. "created_at:>=2026-09-01 status:open". */
    async listOrders({ search = 'status:open', max = 250 } = {}) {
      const out = [];
      let after = null;
      while (out.length < max) {
        const data = await gql(Q.ORDERS_QUERY, { first: Math.min(50, max - out.length), after, query: search });
        out.push(...data.orders.nodes.map(mapOrder));
        if (!data.orders.pageInfo.hasNextPage) break;
        after = data.orders.pageInfo.endCursor;
      }
      return out;
    },

    async getOrder(gid) {
      const data = await gql(Q.ORDER_QUERY, { id: gid });
      return data.order ? mapOrder(data.order) : null;
    },

    /** Fulfills all open fulfillment orders with the AWB as tracking. Returns the fulfillment id. */
    async fulfill(order, { awb, company, url, notifyCustomer }) {
      const open = order.fulfillmentOrders.filter((f) => ['OPEN', 'IN_PROGRESS'].includes(f.status));
      if (!open.length) {
        throw new ProcessingError({
          code: 'SHOPIFY_NOTHING_TO_FULFILL',
          message: 'Comanda nu mai are produse de expediat în Shopify.',
          hint: 'Probabil a fost marcată ca expediată manual. Nu e nevoie de nimic; AWB-ul rămâne salvat aici.',
          provider: 'shopify',
        });
      }
      const res = await gql(Q.FULFILL_MUTATION, {
        fulfillment: {
          lineItemsByFulfillmentOrder: open.map((f) => ({ fulfillmentOrderId: f.id })),
          trackingInfo: { number: awb, company, url },
          notifyCustomer: !!notifyCustomer,
        },
      });
      return userErrors(res.fulfillmentCreate, 'expedierea').fulfillment;
    },

    async cancelFulfillment(id) {
      return userErrors((await gql(Q.FULFILLMENT_CANCEL_MUTATION, { id })).fulfillmentCancel, 'anularea expedierii');
    },

    async markAsPaid(gid) {
      return userErrors((await gql(Q.MARK_PAID_MUTATION, { input: { id: gid } })).orderMarkAsPaid, 'marcarea ca plătită');
    },

    async addTags(gid, tags) {
      if (!tags?.length) return;
      return userErrors((await gql(Q.TAGS_ADD_MUTATION, { id: gid, tags })).tagsAdd, 'etichetele');
    },

    async registerWebhooks(baseUrl) {
      const topics = ['ORDERS_CREATE', 'ORDERS_UPDATED', 'ORDERS_CANCELLED', 'APP_UNINSTALLED'];
      const results = [];
      for (const topic of topics) {
        const res = await gql(Q.WEBHOOK_CREATE_MUTATION, { topic, sub: { uri: `${baseUrl}/webhooks/shopify`, format: 'JSON' } });
        const errs = res.webhookSubscriptionCreate.userErrors;
        // "Address for this topic has already been taken" means it's already registered.
        results.push({ topic, ok: !errs.length || errs.every((e) => /taken/i.test(e.message)), errors: errs });
      }
      return results;
    },
  };
}
