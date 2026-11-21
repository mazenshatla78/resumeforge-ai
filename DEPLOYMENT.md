# Deployment — ResumeForge AI

## Requirements
- Python 3.11+
- HTTPS in production (use reverse proxy: nginx/Caddy/Cloudflare).
- Set strong `JWT_SECRET` (>=32 bytes).
- Set `ADMIN_BOOTSTRAP_SECRET`, then clear after bootstrap.

## Steps
1. Clone repo, create virtualenv, `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`, fill secrets.
3. Set `ALLOWED_ORIGINS` to your domain.
4. Set `APP_BASE_URL` to your public URL.
5. Run: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
   - Or use systemd/supervisor/Docker.
6. Configure reverse proxy with HTTPS and forward to port 8000.

## Database
- Default SQLite. For production scale, set `DATABASE_URL` to PostgreSQL.
- Back up `data/app.db` regularly.

## Security checklist
- [ ] HTTPS enforced
- [ ] Strong JWT_SECRET
- [ ] ADMIN_BOOTSTRAP_SECRET cleared after bootstrap
- [ ] .env not committed
- [ ] ALLOWED_ORIGINS restricted
- [ ] Rate limits appropriate
- [ ] Backups configured

## Monitoring
- Check `/api/health`.
- Review audit logs via admin dashboard.
- Monitor webhook_events for failures.
