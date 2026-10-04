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
  // Shown next to the publisher's name on /privacy, /terms (and /confidentialitate, /termeni) (e.g. "CUI ..., sediu ...").
  publisherDetails: env.PUBLISHER_DETAILS || '',
  shopify: {
    apiKey: env.SHOPIFY_API_KEY || '',
    apiSecret: env.SHOPIFY_API_SECRET || '',
    apiVersion: env.SHOPIFY_API_VERSION || '2026-07',
    scopes: env.SHOPIFY_SCOPES || 'read_orders,write_orders,read_merchant_managed_fulfillment_orders,write_merchant_managed_fulfillment_orders',
    // Stores in the app's own organization (e.g. a dev store), connected with the client credentials grant
    // instead of OAuth: no public URL or install flow needed. Comma-separated *.myshopify.com domains.
    ownStores: (env.SHOPIFY_OWN_STORES || '').split(',').map((s) => s.trim()).filter(Boolean),
    // App handle (shopify.app.toml `handle`): part of the plan selection page URL
    // https://admin.shopify.com/store/{store_handle}/charges/{app_handle}/pricing_plans
    appHandle: env.SHOPIFY_APP_HANDLE || 'expedo',
    // Shopify App Pricing reads the subscription through the Partner API (Active Subscription API).
    // Without these, the app falls back to the Admin API (currentAppInstallation.activeSubscriptions).
    partner: {
      orgId: env.SHOPIFY_PARTNER_ORG_ID || '',
      token: env.SHOPIFY_PARTNER_API_TOKEN || '',
      appGid: env.SHOPIFY_APP_GID || '',
      apiVersion: env.SHOPIFY_PARTNER_API_VERSION || '2026-07',
    },
  },
  workerIntervalMs: Number(env.WORKER_INTERVAL_MS || 5000),
  trackingIntervalMinutes: Number(env.TRACKING_INTERVAL_MINUTES || 30),
  sessionSecret: env.SESSION_SECRET || env.APP_SECRET || randomBytes(32).toString('hex'),
};

if (!config.appSecret) {
  throw new Error('APP_SECRET is required in production (used to encrypt customer data and saved credentials).');
}
if (env.NODE_ENV === 'production' && config.adminPassword && config.adminPassword.length < 12) {
  console.warn('ADMIN_PASSWORD is too short: use at least 16 random characters (docs/security.md).');
}
