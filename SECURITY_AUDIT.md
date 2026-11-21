# Security Audit — ResumeForge AI

## Implemented protections
- [x] Argon2id password hashing (bcrypt legacy support)
- [x] JWT with expiry, suspended-account check
- [x] Rate limiting (auth, AI, uploads)
- [x] CORS restricted origins
- [x] Security headers + CSP
- [x] Global error handler (no stack traces)
- [x] Upload validation (extension + magic bytes + size)
- [x] Input truncation (AI)
- [x] Prompt-injection hardening in system prompts
- [x] Ownership checks on resumes, optimizations, job descriptions, exports
- [x] Admin RBAC (server-side)
- [x] Admin bootstrap (one-time, secret-gated)
- [x] Audit logging (admin actions, auth events)
- [x] Webhook signature verification
- [x] Idempotent webhook processing
- [x] No secrets in frontend
- [x] Account deletion + data export

## Known limitations / not implemented
- [ ] CSRF tokens — mitigated by Bearer-token-in-header pattern; recommend SameSite cookies if moving to cookie auth.
- [ ] Email delivery — SMTP not configured; reset/verify links logged to console in dev. Configure SMTP_* env vars for production.
- [ ] MFA — not implemented (documented as future).
- [ ] Database encryption at rest — relies on host/volume encryption.
- [ ] Dependency vulnerability scanning — run `pip audit` periodically.
- [ ] WAF / DDoS protection — handle at reverse proxy / CDN level.

## Testing performed
- pytest: 12 tests pass (auth, ownership, admin RBAC, webhook signatures, provider availability).
- Manual: register/login/optimize/export/admin bootstrap end-to-end.

## Secrets check
- `.env` excluded from git (ensure `.gitignore` includes it).
- No API keys in frontend bundle.
