# Database Migration: SQLite → PostgreSQL

## Overview
ResumeForge AI uses SQLAlchemy, so switching to PostgreSQL is straightforward.

## Steps

1. Install PostgreSQL (14+ recommended) and create a database:
   ```sql
   CREATE DATABASE resumeforge;
   CREATE USER resumeforge_user WITH PASSWORD 'your_strong_password';
   GRANT ALL PRIVILEGES ON DATABASE resumeforge TO resumeforge_user;
   ```

2. Install the PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

3. Update `.env`:
   ```
   DATABASE_URL=postgresql+psycopg2://resumeforge_user:your_strong_password@localhost:5432/resumeforge
   ```

4. Remove the SQLite-specific code (already conditional in `database.py`):
   - `connect_args={"check_same_thread": False}` is only applied for SQLite.
   - The parent-dir creation is SQLite-only.

5. Run the app — SQLAlchemy will create tables automatically via `init_db()` on startup:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

6. (Optional) For production, use Alembic for migrations:
   ```bash
   pip install alembic
   alembic init alembic
   # configure alembic.ini with your DATABASE_URL
   alembic revision --autogenerate -m "initial"
   alembic upgrade head
   ```

## Notes
- All models use standard SQLAlchemy types compatible with PostgreSQL.
- JSON columns use `JSON` type (works with PostgreSQL's jsonb via SQLAlchemy).
- Boolean columns use `Boolean` (PostgreSQL native boolean).
- No SQLite-specific SQL is used.
- Back up your SQLite data before migrating; use a script to copy rows if needed.
- Set `DATABASE_URL` in your deployment environment (never commit it).
