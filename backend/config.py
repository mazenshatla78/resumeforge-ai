import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "openai/gpt-oss-20b")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "data", "app.db").replace("\\", "/"))

# CORS
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if o.strip()]

# Security
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "50000"))
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")
RATE_LIMIT_AI = os.getenv("RATE_LIMIT_AI", "10/minute")

# SMTP (optional; if not configured, reset/verify links are logged to console in dev)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@resumeforge.ai")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

# Admin bootstrap (one-time)
ADMIN_BOOTSTRAP_SECRET = os.getenv("ADMIN_BOOTSTRAP_SECRET", "")

# Payments — Paddle (international)
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY", "")
PADDLE_CLIENT_TOKEN = os.getenv("PADDLE_CLIENT_TOKEN", "")
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET", "")
PADDLE_ENVIRONMENT = os.getenv("PADDLE_ENVIRONMENT", "sandbox")  # sandbox | production
PADDLE_PRICE_MONTHLY = os.getenv("PADDLE_PRICE_MONTHLY", "")
PADDLE_PRICE_ANNUAL = os.getenv("PADDLE_PRICE_ANNUAL", "")

# Payments — Paymob (Egypt)
PAYMOB_API_KEY = os.getenv("PAYMOB_API_KEY", "")
PAYMOB_SECRET_KEY = os.getenv("PAYMOB_SECRET_KEY", "")
PAYMOB_PUBLIC_KEY = os.getenv("PAYMOB_PUBLIC_KEY", "")
PAYMOB_INTEGRATION_ID = os.getenv("PAYMOB_INTEGRATION_ID", "")
PAYMOB_IFRAME_ID = os.getenv("PAYMOB_IFRAME_ID", "")
PAYMOB_WEBHOOK_SECRET = os.getenv("PAYMOB_WEBHOOK_SECRET", "")

FREE_MONTHLY_LIMIT = int(os.getenv("FREE_MONTHLY_LIMIT", "3"))
PREMIUM_MONTHLY_PRICE = 19.00
PREMIUM_ANNUAL_PRICE = 149.00

APP_NAME = "ResumeForge AI"
APP_VERSION = "1.0.0"
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
