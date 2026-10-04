import { shopifyClient } from './client.js';

// Demo stores have no Shopify behind them: reads come from the local DB, writes are no-ops.
const demoClient = {
  async shopInfo() { return { id: 'gid://shopify/Shop/0', name: 'Magazin demo', myshopifyDomain: 'demo.myshopify.com', currencyCode: 'RON' }; },
  async listOrders() { return []; },
  async getOrder() { return null; },
  async fulfill() { return { id: `gid://shopify/Fulfillment/demo-${Date.now()}` }; },
  async cancelFulfillment() {},
  async markAsPaid() {},
  async addTags() {},
  async registerWebhooks() { return []; },
  async activeSubscription() { return null; },
};

export function getShopify(store) {
  return store.demo ? demoClient : shopifyClient(store);
}
