# ResumeForge AI — Implementation Plan

## 1. Current architecture
- **Backend:** FastAPI (Python 3.14), SQLAlchemy ORM, SQLite. Routers: auth, resumes, optimize, billing, export.
- **Frontend:** Vanilla JS SPA served by FastAPI, Tailwind v4 browser build.
- **AI:** Groq (openai/gpt-oss-120b) via server-side client.
- **Auth:** JWT (HS256, 7-day), bcrypt password hashing.
- **Payments:** Stripe skeleton + demo upgrade (to be replaced by Paddle + Paymob).
- **Storage:** Resumes/optimizations in SQLite; no file storage on disk.

## 2. Existing functionality
- Register/login/logout, JWT sessions.
- Resume CRUD + PDF/DOCX/TXT upload & parsing.
- Job description CRUD.
- AI optimization: ATS score, keyword gaps, tailored resume, cover letter, interview prep.
- Free (3/mo) vs Premium gating.
- PDF/DOCX export.
- Basic billing status + demo upgrade + Stripe checkout/webhook skeleton.

## 3. Security weaknesses (identified)
- CORS `allow_origins=["*"]` with credentials — too permissive.
- No rate limiting on auth or AI endpoints.
- No security headers / CSP.
- Password hashing bcrypt (acceptable but spec prefers Argon2id) — upgrading to Argon2id.
- No password reset, no email verification (no email provider configured).
- No input size limits on resume/JD text; no file content validation beyond extension.
- Error messages may leak internals (FastAPI default 500).
- Groq errors surface raw to client in some paths.
- Admin functionality entirely absent.
- No audit logging.
- JWT secret default weak; must be set in prod.
- No CSRF protection (mitigated by Bearer token in header, but add same-origin checks).
- Prompt injection risk: user resume/JD injected into prompts; mitigate with input truncation + system-prompt hardening.
- No ownership check on some reads (mostly present; verify all).

## 4. Missing features
- Admin dashboard (RBAC, bootstrap, audit logs, stats, user/subscription/AI/payment management, system settings).
- Paddle + Paymob payment integrations with webhooks, idempotency, availability checks.
- Subscription lifecycle (expiry, cancellation, grace period, refunds/chargebacks).
- Account deletion, data export, privacy/retention policy docs.
- Email verification & password reset (requires email provider; implement token flow + dev-mode link logging).
- MFA (optional; document as future).
- Automated tests.

## 5. Required database changes
- Add `role` (user/admin) to users; `email_verified`, `is_suspended`, `suspended_at`, `suspended_reason`.
- Add `Subscription` table (provider, plan, status, external ids, period dates, cancel_at_period_end).
- Add `Payment` table (provider, transaction id, status, amount, currency, user, timestamps, idempotency key).
- Add `WebhookEvent` table (provider, event id, processed flag, payload hash, timestamps) for idempotency.
- Add `AuditLog` table (actor, action, target, metadata, ip, timestamp).
- Add `PasswordResetToken`, `EmailVerificationToken` tables.
- Add `SystemSetting` table (key, value, updated_by, updated_at).
- Add `AdminBootstrapToken` (one-time setup).
- Add usage limits per plan in settings (keep env default).

## 6. Payment integration plan
- Abstract `PaymentProvider` interface with `create_checkout`, `verify_webhook`, `parse_event`.
- Paddle: official API v1 (subscriptions), webhook signature verification via Paddle-Signature header.
- Paymob: acceptance API (auth token, order registration, payment key, iframe), HMAC webhook verification.
- Availability: each provider independently enabled based on env config presence + admin toggle + health.
- Webhook idempotency via WebhookEvent table.
- Entitlements updated only after verified webhook.
- Friendly unavailable messages; never leak internals.

## 7. Admin dashboard plan
- Separate `/admin` route group + frontend admin pages.
- Bootstrap: protected one-time setup endpoint gated by `ADMIN_BOOTSTRAP_SECRET` env; creates first admin; disables after success.
- RBAC: `role` column; admin endpoints require `require_admin` dependency.
- Audit logging on all admin actions.
- Sections: Overview, Users, Subscriptions, AI Usage, Payments, Audit Logs, System Settings, Payment Gateways.

## 8. Testing and deployment plan
- pytest: auth, authorization, ownership, payment webhook signature/idempotency, AI limit enforcement, upload validation.
- Security: SQLi/XSS checks (input validation), secret exposure scan.
- Deployment: DEPLOYMENT.md with env vars, HTTPS, reverse proxy, backups; Docker optional.
- Document implemented vs pending vs waiting for credentials.

## Phases execution order
1. Security hardening (auth, headers, CORS, rate limit, upload validation, error handling).
2. Database migrations + new models.
3. Admin dashboard backend + frontend + bootstrap.
4. Payment architecture (Paddle + Paymob) + availability + admin controls.
5. Privacy features (deletion, export).
6. Tests.
7. Documentation.
