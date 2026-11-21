# Payments Setup — ResumeForge AI

## Overview
Two providers:
- **Paddle** — international customers (subscriptions).
- **Paymob** — Egyptian customers.

Each provider is independently configured and toggled. If unconfigured, it is hidden and returns a friendly unavailable message. The other provider keeps working.

## Paddle setup
1. Create a Paddle account (sandbox first).
2. Create two prices: Monthly $19, Annual $149.
3. Set env vars:
   - `PADDLE_API_KEY`
   - `PADDLE_CLIENT_TOKEN`
   - `PADDLE_WEBHOOK_SECRET`
   - `PADDLE_ENVIRONMENT` = `sandbox` or `production`
   - `PADDLE_PRICE_MONTHLY` (price id)
   - `PADDLE_PRICE_ANNUAL` (price id)
4. Configure webhook endpoint: `https://your-domain/api/billing/webhook/paddle`
   - Subscribe to: transaction.completed, subscription.canceled, subscription.updated
5. Verify `Paddle-Signature` header (handled server-side).

## Paymob setup
1. Create a Paymob merchant account.
2. Create an integration (card) and an iframe.
3. Set env vars:
   - `PAYMOB_API_KEY`
   - `PAYMOB_SECRET_KEY`
   - `PAYMOB_PUBLIC_KEY`
   - `PAYMOB_INTEGRATION_ID`
   - `PAYMOB_IFRAME_ID`
   - `PAYMOB_WEBHOOK_SECRET` (HMAC secret from dashboard)
4. Configure callback/webhook: `https://your-domain/api/billing/webhook/paymob`
5. HMAC verification handled server-side.

## Testing
- Use sandbox/test credentials only.
- Test successful, failed, pending, duplicate webhook events.
- Verify Premium entitlement only changes after verified webhook.

## Status
- **Implemented:** provider abstraction, checkout initiation, webhook handlers, signature verification, idempotency, availability checks, admin gateway view.
- **Waiting for credentials:** both providers (no keys configured yet).
- **Not tested against real providers:** sandbox checkout flow (requires merchant accounts).
- **Limitations:** Paymob recurring subscriptions depend on account capabilities; documented as such.
