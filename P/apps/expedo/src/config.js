import { randomBytes } from 'node:crypto';

const env = process.env;

export const config = {
  port: Number(env.PORT || 3000),
  appUrl: (env.APP_URL || `http://localhost:${env.PORT || 3000}`).replace(/\/$/, ''),
  dbFile: env.DB_FILE || 'data/expedo.db',
  // Encrypts customer data, courier/invoicing credentials and Shopify tokens at rest. Must be stable in production.
  appSecret: env.APP_SECRET || (env.NODE_ENV === 'production' ? null : 'dev-only-secret-change-me'),
  // Standalone dashboard login (outside the Shopify admin).
  adminPassword: env.ADMIN_PASSWORD || '',
  demo: env.DEMO === '1',
  // Shown next to the publisher's name on /confidentialitate and /termeni (e.g. "CUI ..., sediu ...").
  publisherDetails: env.PUBLISHER_DETAILS || '',
  shopify: {
    apiKey: env.SHOPIFY_API_KEY || '',
    apiSecret: env.SHOPIFY_API_SECRET || '',
    apiVersion: env.SHOPIFY_API_VERSION || '2026-07',
    scopes: env.SHOPIFY_SCOPES || 'read_orders,write_orders,read_merchant_managed_fulfillment_orders,write_merchant_managed_fulfillment_orders',
    // Stores in the app's own organization (e.g. a dev store), connected with the client credentials grant
    // instead of OAuth: no public URL or install flow needed. Comma-separated *.myshopify.com domains.
    ownStores: (env.SHOPIFY_OWN_STORES || '').split(',').map((s) => s.trim()).filter(Boolean),
  },
  workerIntervalMs: Number(env.WORKER_INTERVAL_MS || 5000),
  trackingIntervalMinutes: Number(env.TRACKING_INTERVAL_MINUTES || 30),
  sessionSecret: env.SESSION_SECRET || env.APP_SECRET || randomBytes(32).toString('hex'),
};

if (!config.appSecret) {
  throw new Error('APP_SECRET is required in production (used to encrypt customer data and saved credentials).');
}
if (env.NODE_ENV === 'production' && config.adminPassword && config.adminPassword.length < 12) {
  console.warn('ADMIN_PASSWORD e prea scurtă: folosește cel puțin 16 caractere aleatorii (docs/securitate.md).');
}
