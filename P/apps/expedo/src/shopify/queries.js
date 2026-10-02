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
  totalDiscountsSet { ...Money }
  totalOutstandingSet { ...Money }
  shippingAddress { ...Addr }
  billingAddress { ...Addr }
  shippingLines(first: 5, includeRemovals: false) { nodes { title code source originalPriceSet { ...Money } discountedPriceSet { ...Money } taxLines { rate } } }
  lineItems(first: 100) { nodes { id name title variantTitle sku quantity currentQuantity requiresShipping isGiftCard originalUnitPriceSet { ...Money } discountAllocations { allocatedAmountSet { ...Money } } taxLines { rate } } }
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

export const SHOP_QUERY = `query { shop { name myshopifyDomain currencyCode } }`;

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
