import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.rate_limit import limiter
from backend.database import init_db
from backend.config import FRONTEND_DIR, ALLOWED_ORIGINS
from backend.routers import auth, resumes, optimize, billing, export, admin

app = FastAPI(title="ResumeForge AI", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # CSP: allow tailwind browser build + inline styles/scripts used by app
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.paddle.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://cdn.paddle.com; "
        "font-src 'self' data:; "
        "connect-src 'self' https://api.paddle.com https://sandbox-api.paddle.com; "
        "frame-src https://checkout.paddle.com https://sandbox-checkout.paddle.com; "
        "frame-ancestors 'none';"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Avoid leaking internals
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(optimize.router)
app.include_router(billing.router)
app.include_router(export.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "ResumeForge AI"}


@app.get("/tailwindcss")
def tailwind_stub():
    from fastapi.responses import Response
    return Response(content="/* */", media_type="text/css")


# Serve frontend
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/admin")
    def admin_page():
        p = os.path.join(FRONTEND_DIR, "admin.html")
        if os.path.isfile(p):
            return FileResponse(p)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    for _route, _file in [("/login", "login.html"), ("/signup", "signup.html"),
                           ("/about", "about.html"), ("/contact", "contact.html"),
                           ("/pricing", "pricing.html"), ("/welcome", "welcome.html")]:
        def _make(fp):
            def _handler():
                if os.path.isfile(fp):
                    return FileResponse(fp)
                return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
            return _handler
        app.add_api_route(_route, _make(os.path.join(FRONTEND_DIR, _file)), methods=["GET"])

    @app.get("/privacy")
    def privacy_page():
        p = os.path.join(FRONTEND_DIR, "privacy.html")
        if os.path.isfile(p):
            return FileResponse(p)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/")
    def index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
