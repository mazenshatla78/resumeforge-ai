# Admin Guide — ResumeForge AI

## First admin bootstrap
1. Set `ADMIN_BOOTSTRAP_SECRET` in `.env`.
2. Restart server.
3. POST `/api/admin/bootstrap` with `{ "secret": "...", "email": "...", "password": "..." }`.
   - Or use curl. Minimum password 8 chars.
4. Bootstrap disables itself after the first admin is created.
5. Log in at `/admin` with the admin credentials.

## Admin dashboard
URL: `http://your-domain/admin`

Sections:
- **Overview** — real DB-backed stats (users, scans, revenue, failed payments).
- **Users** — search/filter, suspend/reactivate.
- **Subscriptions** — list with status/period.
- **Payments** — transactions with status.
- **AI Usage** — scans per user.
- **Audit Logs** — admin actions.
- **Settings** — free limit, prices, maintenance mode, gateway toggles.
- **Gateways** — configuration status.

## Security
- Admin endpoints require `role == "admin"` (server-side).
- All admin actions are audit-logged.
- Never hardcode admin credentials.
- Rotate `ADMIN_BOOTSTRAP_SECRET` after bootstrap (set empty).
- MFA not implemented; recommended via reverse proxy or future work.

## Managing gateways
- Toggle via Settings: `paddle_enabled`, `paymob_enabled`.
- Gateway shows configured/enabled status.
- Never expose secret values through the dashboard.
