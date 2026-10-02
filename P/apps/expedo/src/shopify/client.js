import { config } from '../config.js';
import { request } from '../lib/http.js';
import { ProcessingError } from '../core/errors.js';
import { m } from '../i18n/index.js';
import * as Q from './queries.js';
import { mapOrder } from './mapper.js';
import { clientCredentialsToken } from './auth.js';
import { storeCache } from '../db.js';

const isOwnStore = (store) => config.shopify.ownStores.includes(store.shop);

/** Own-organization stores get a fresh client-credentials token when the cached one is gone. */
async function accessToken(store, { refresh = false } = {}) {
  if (!isOwnStore(store)) return store.accessToken;
  const cache = storeCache(store.id);
  if (!refresh) {
    const cached = cache.get('shopify:cc-token');
    if (cached) return cached;
  }
  const t = await clientCredentialsToken(store.shop);
  cache.set('shopify:cc-token', t.access_token, Math.max(60, Number(t.expires_in || 86400) - 600));
  return t.access_token;
}

// Admin GraphQL client for one store. Demo stores have no token and never reach this.

export function shopifyClient(store) {
  async function gql(query, variables = {}) {
    let token = await accessToken(store);
    if (!token) {
      throw new ProcessingError({ code: 'SHOPIFY_NOT_CONNECTED', provider: 'shopify' });
    }
    const url = `https://${store.shop}/admin/api/${config.shopify.apiVersion}/graphql.json`;
    for (let attempt = 0; ; attempt++) {
      let body;
      try {
        ({ body } = await request('Shopify', url, {
          method: 'POST',
          headers: { 'X-Shopify-Access-Token': token },
          json: { query, variables },
        }));
      } catch (err) {
        // An expired client-credentials token: get a new one once.
        if (err.code === 'AUTH_FAILED' && isOwnStore(store) && attempt === 0) {
          token = await accessToken(store, { refresh: true });
          continue;
        }
        throw err;
      }
      const throttled = body?.errors?.some?.((e) => e?.extensions?.code === 'THROTTLED');
      if (throttled && attempt < 3) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      if (body?.errors?.length) {
        throw new ProcessingError({
          code: 'SHOPIFY_GRAPHQL',
          params: { text: body.errors.map((e) => e.message).join('; ') },
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
        params: { what: m(`errors.SHOPIFY_USER_ERROR.what.${what}`), text: errs.map((e) => e.message).join('; ') },
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
      return userErrors(res.fulfillmentCreate, 'fulfillment').fulfillment;
    },

    async cancelFulfillment(id) {
      return userErrors((await gql(Q.FULFILLMENT_CANCEL_MUTATION, { id })).fulfillmentCancel, 'fulfillmentCancel');
    },

    async markAsPaid(gid) {
      return userErrors((await gql(Q.MARK_PAID_MUTATION, { input: { id: gid } })).orderMarkAsPaid, 'markPaid');
    },

    async addTags(gid, tags) {
      if (!tags?.length) return;
      return userErrors((await gql(Q.TAGS_ADD_MUTATION, { id: gid, tags })).tagsAdd, 'tags');
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
