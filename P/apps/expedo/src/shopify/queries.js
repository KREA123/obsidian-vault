// Admin GraphQL operations, validated against the Shopify Admin schema.
// Customer fields are read from the order addresses, so the app does not need read_customers.

const FRAGMENTS = `
fragment Money on MoneyBag { shopMoney { amount currencyCode } }
fragment Addr on MailingAddress { firstName lastName name company address1 address2 city province provinceCode zip countryCodeV2 phone }
fragment OrderFields on Order {
  id name createdAt cancelledAt closed test
  currencyCode taxesIncluded
  displayFinancialStatus displayFulfillmentStatus
  paymentGatewayNames
  email phone note tags
  totalWeight
  customAttributes { key value }
  totalPriceSet { ...Money }
  subtotalPriceSet { ...Money }
  totalShippingPriceSet { ...Money }
  currentTotalPriceSet { ...Money }
  currentSubtotalPriceSet { ...Money }
  currentShippingPriceSet { ...Money }
  currentTotalDiscountsSet { ...Money }
  totalDiscountsSet { ...Money }
  totalOutstandingSet { ...Money }
  shippingAddress { ...Addr }
  billingAddress { ...Addr }
  shippingLines(first: 5, includeRemovals: false) { nodes { title code source originalPriceSet { ...Money } discountedPriceSet { ...Money } taxLines { rate priceSet { ...Money } } } }
  lineItems(first: 100) { nodes { id name title variantTitle sku quantity currentQuantity requiresShipping isGiftCard originalUnitPriceSet { ...Money } discountAllocations { allocatedAmountSet { ...Money } } taxLines { rate priceSet { ...Money } } } }
  fulfillmentOrders(first: 10) { nodes { id status assignedLocation { name } } }
}`;

export const ORDERS_QUERY = `
query Orders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query, sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    nodes { ...OrderFields }
  }
}
${FRAGMENTS}`;

export const ORDER_QUERY = `
query Order($id: ID!) { order(id: $id) { ...OrderFields } }
${FRAGMENTS}`;

export const SHOP_QUERY = `query { shop { id name myshopifyDomain currencyCode } }`;

// Legacy / fallback source of the plan (Billing API subscriptions; managed-pricing apps enrolled before
// April 2026). Dev-store test charges are ACTIVE with test: true and count as active.
export const CURRENT_PLAN_QUERY = `
query CurrentPlan {
  currentAppInstallation {
    activeSubscriptions {
      id name status trialDays createdAt currentPeriodEnd test
      lineItems { plan { pricingDetails { __typename ... on AppRecurringPricing { interval price { amount currencyCode } } } } }
    }
  }
}`;

// Partner API (not the Admin API): Shopify App Pricing's Active Subscription API, 2026-07.
// Returns null when the shop has no active subscription. Written from the shopify.dev reference.
export const PARTNER_ACTIVE_SUBSCRIPTION_QUERY = `
query ActiveSubscription($appId: ID!, $shopId: ID!) {
  activeSubscription(appId: $appId, shopId: $shopId) {
    billingPeriod cancelAtEndOfCycle trialEndsAt
    currentBillingCycle { startTime endTime }
    items { handle description price { __typename active currency ... on FlatRatePrice { amount } } }
  }
}`;

export const FULFILL_MUTATION = `
mutation Fulfill($fulfillment: FulfillmentInput!) {
  fulfillmentCreate(fulfillment: $fulfillment) {
    fulfillment { id status trackingInfo { number url company } }
    userErrors { field message }
  }
}`;

export const FULFILLMENT_CANCEL_MUTATION = `
mutation Cancel($id: ID!) { fulfillmentCancel(id: $id) { fulfillment { id status } userErrors { field message } } }`;

export const MARK_PAID_MUTATION = `
mutation MarkPaid($input: OrderMarkAsPaidInput!) {
  orderMarkAsPaid(input: $input) { order { id displayFinancialStatus } userErrors { field message } }
}`;

export const TAGS_ADD_MUTATION = `
mutation Tag($id: ID!, $tags: [String!]!) { tagsAdd(id: $id, tags: $tags) { userErrors { field message } } }`;

export const WEBHOOK_CREATE_MUTATION = `
mutation Hook($topic: WebhookSubscriptionTopic!, $sub: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $sub) { webhookSubscription { id } userErrors { field message } }
}`;
