# Security Policy — ResumeForge AI

## Reporting
Report security issues privately to the project owner. Do not open public issues for vulnerabilities.

## Secrets
- Never commit `.env` or any credential. `.env` is gitignored.
- All secrets are read from environment variables via `backend/config.py`.
- The Groq API key is server-side only and never sent to the frontend.

## Authentication
- Passwords hashed with Argon2id (with bcrypt verification for legacy hashes).
- JWT sessions expire (default 7 days). Suspended accounts are blocked.
- Rate limiting on auth endpoints (default 5/min).
- Password reset and email verification use hashed, expiring, single-use tokens.

## Authorization
- All user-owned resources are scoped by `user_id` in queries.
- Admin endpoints require `role == "admin"` via `require_admin` dependency (server-side).
- Ownership is verified before read/update/delete.

## File uploads
- Extension + magic-byte validation.
- Size limit (default 5 MB).
- Text truncated to configured max.

## API hardening
- CORS restricted to `ALLOWED_ORIGINS`.
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP.
- Global exception handler hides internal errors.
- Rate limiting on AI and auth endpoints.
- Input truncation for AI prompts; prompt-injection hardening in system prompts.

## Data protection
- Resumes stored in DB; no public URLs.
- Account deletion cascades to user data.
- Data export endpoint available.
- Resume contents are never logged.

## Payments
- Entitlements granted only after verified webhook.
- Webhook signature verification (Paddle HMAC, Paymob HMAC).
- Idempotent webhook processing via `webhook_events` table.
- No card data stored.
