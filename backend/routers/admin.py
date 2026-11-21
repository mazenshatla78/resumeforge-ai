import os
import secrets
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.database import get_db
from backend.models import (User, Optimization, UsageLog, Subscription, Payment, WebhookEvent,
                           AuditLog, SystemSetting, AdminBootstrapToken)
from backend.deps import get_current_user, require_admin, audit, client_ip
from backend.auth import hash_password, verify_password, create_token
from backend.config import ADMIN_BOOTSTRAP_SECRET, FREE_MONTHLY_LIMIT
from backend.rate_limit import limiter

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------- Bootstrap ----------
class BootstrapIn(BaseModel):
    secret: str
    username: str
    password: str
    name: str = "Administrator"


@router.post("/bootstrap")
@limiter.limit("3/minute")
def bootstrap(request: Request, data: BootstrapIn, db: Session = Depends(get_db)):
    # If any admin exists, bootstrap is disabled
    if db.query(User).filter(User.role == "admin").first():
        raise HTTPException(403, "Admin bootstrap already completed")
    if not ADMIN_BOOTSTRAP_SECRET or data.secret != ADMIN_BOOTSTRAP_SECRET:
        raise HTTPException(403, "Invalid bootstrap secret")
    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    username = data.username.strip()[:80]
    if not username:
        raise HTTPException(400, "Username required")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Username already taken")
    u = User(username=username, password_hash=hash_password(data.password), name=data.name.strip()[:120],
             role="admin", email_verified=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    audit(db, u, "admin.bootstrap", "user", u.id, ip=client_ip(request))
    return {"ok": True, "message": "Admin account created. Bootstrap is now disabled."}


# ---------- Admin login ----------
class AdminLoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
@limiter.limit("5/minute")
def admin_login(request: Request, data: AdminLoginIn, db: Session = Depends(get_db)):
    uname = data.username.strip()
    u = db.query(User).filter(User.username == uname).first()
    if not u or u.role != "admin" or not verify_password(data.password, u.password_hash):
        audit(db, None, "admin.login_failed", "user", None, metadata={"username": uname}, ip=client_ip(request))
        raise HTTPException(401, "Invalid admin credentials")
    if u.is_suspended:
        raise HTTPException(403, "Account suspended")
    u.last_login_at = datetime.utcnow()
    db.commit()
    audit(db, u, "admin.login", "user", u.id, ip=client_ip(request))
    token = create_token(u.id, u.email)
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "token": token}


# ---------- Overview ----------
@router.get("/overview")
def overview(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    free_users = db.query(func.count(User.id)).filter(User.plan == "free").scalar() or 0
    premium_users = db.query(func.count(User.id)).filter(User.plan == "premium").scalar() or 0
    admin_users = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
    suspended = db.query(func.count(User.id)).filter(User.is_suspended == True).scalar() or 0
    total_scans = db.query(func.count(UsageLog.id)).filter(UsageLog.action == "optimize").scalar() or 0
    total_opts = db.query(func.count(Optimization.id)).scalar() or 0
    # last 30 days registrations
    since = datetime.utcnow() - timedelta(days=30)
    new_30 = db.query(func.count(User.id)).filter(User.created_at >= since).scalar() or 0
    # revenue from succeeded payments
    revenue = db.query(func.coalesce(func.sum(Payment.amount), 0.0)).filter(Payment.status == "succeeded").scalar() or 0.0
    payments_count = db.query(func.count(Payment.id)).scalar() or 0
    failed_payments = db.query(func.count(Payment.id)).filter(Payment.status == "failed").scalar() or 0
    pending_payments = db.query(func.count(Payment.id)).filter(Payment.status == "pending").scalar() or 0
    webhooks_failed = db.query(func.count(WebhookEvent.id)).filter(WebhookEvent.processed == False).scalar() or 0
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    recent_payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(10).all()
    return {
        "total_users": total_users,
        "free_users": free_users,
        "premium_users": premium_users,
        "admin_users": admin_users,
        "suspended_users": suspended,
        "total_scans": total_scans,
        "total_optimizations": total_opts,
        "new_users_30d": new_30,
        "revenue_total": round(float(revenue), 2),
        "payments_total": payments_count,
        "payments_failed": failed_payments,
        "payments_pending": pending_payments,
        "webhooks_failed": webhooks_failed,
        "recent_users": [{"id": u.id, "email": u.email, "plan": u.plan, "role": u.role, "created_at": u.created_at.isoformat()} for u in recent_users],
        "recent_payments": [{"id": p.id, "user_id": p.user_id, "provider": p.provider, "plan": p.plan, "amount": p.amount, "currency": p.currency, "status": p.status, "created_at": p.created_at.isoformat()} for p in recent_payments],
    }


# ---------- Users ----------
@router.get("/users")
def list_users(q: str = "", plan: str = "", role: str = "", suspended: str = "", page: int = 1, page_size: int = 25,
               admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.email.ilike(like)) | (User.name.ilike(like)))
    if plan:
        query = query.filter(User.plan == plan)
    if role:
        query = query.filter(User.role == role)
    if suspended == "true":
        query = query.filter(User.is_suspended == True)
    elif suspended == "false":
        query = query.filter(User.is_suspended == False)
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "users": [{"id": u.id, "email": u.email, "username": u.username, "name": u.name, "role": u.role, "plan": u.plan,
                   "email_verified": u.email_verified, "is_suspended": u.is_suspended, "created_at": u.created_at.isoformat(),
                   "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None} for u in rows],
    }


@router.get("/users/{uid}")
def get_user(uid: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(404, "User not found")
    scans = db.query(func.count(UsageLog.id)).filter(UsageLog.user_id == uid, UsageLog.action == "optimize").scalar() or 0
    opts = db.query(func.count(Optimization.id)).filter(Optimization.user_id == uid).scalar() or 0
    payments = db.query(Payment).filter(Payment.user_id == uid).order_by(Payment.created_at.desc()).limit(20).all()
    subs = db.query(Subscription).filter(Subscription.user_id == uid).order_by(Subscription.created_at.desc()).all()
    return {
        "id": u.id, "email": u.email, "name": u.name, "role": u.role, "plan": u.plan,
        "email_verified": u.email_verified, "is_suspended": u.is_suspended,
        "suspended_reason": u.suspended_reason, "created_at": u.created_at.isoformat(),
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "scans": scans, "optimizations": opts,
        "payments": [{"id": p.id, "provider": p.provider, "plan": p.plan, "amount": p.amount, "currency": p.currency, "status": p.status, "created_at": p.created_at.isoformat()} for p in payments],
        "subscriptions": [{"id": s.id, "provider": s.provider, "plan": s.plan, "status": s.status, "period_end": s.current_period_end.isoformat() if s.current_period_end else None, "cancel_at_period_end": s.cancel_at_period_end} for s in subs],
    }


class SuspendIn(BaseModel):
    reason: str = ""


@router.post("/users/{uid}/suspend")
def suspend_user(uid: int, data: SuspendIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(404, "User not found")
    if u.role == "admin":
        raise HTTPException(400, "Cannot suspend admin")
    u.is_suspended = True
    u.suspended_at = datetime.utcnow()
    u.suspended_reason = data.reason[:255]
    db.commit()
    audit(db, admin, "admin.user_suspend", "user", uid, metadata={"reason": data.reason}, ip=client_ip(request))
    return {"ok": True}


@router.post("/users/{uid}/reactivate")
def reactivate_user(uid: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.is_suspended = False
    u.suspended_at = None
    u.suspended_reason = None
    db.commit()
    audit(db, admin, "admin.user_reactivate", "user", uid, ip=client_ip(request))
    return {"ok": True}


class RoleIn(BaseModel):
    role: str


@router.patch("/users/{uid}/role")
def change_role(uid: int, data: RoleIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if data.role not in ("user", "admin"):
        raise HTTPException(400, "Invalid role")
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(404, "User not found")
    old = u.role
    u.role = data.role
    db.commit()
    audit(db, admin, "admin.role_change", "user", uid, metadata={"from": old, "to": data.role}, ip=client_ip(request))
    return {"ok": True}


# ---------- Subscriptions ----------
@router.get("/subscriptions")
def list_subscriptions(status: str = "", provider: str = "", page: int = 1, page_size: int = 25,
                       admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = max(1, page); page_size = min(max(1, page_size), 100)
    q = db.query(Subscription)
    if status:
        q = q.filter(Subscription.status == status)
    if provider:
        q = q.filter(Subscription.provider == provider)
    total = q.count()
    rows = q.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    user_ids = {s.user_id for s in rows}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    return {"total": total, "page": page, "page_size": page_size,
            "subscriptions": [{"id": s.id, "user_id": s.user_id,
                               "user": (users[s.user_id].username or users[s.user_id].email) if s.user_id in users else None,
                               "provider": s.provider, "plan": s.plan, "status": s.status,
                               "period_start": s.current_period_start.isoformat() if s.current_period_start else None,
                               "period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                               "cancel_at_period_end": s.cancel_at_period_end, "created_at": s.created_at.isoformat()} for s in rows]}


# ---------- Payments ----------
@router.get("/payments")
def list_payments(status: str = "", provider: str = "", page: int = 1, page_size: int = 25,
                  admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = max(1, page); page_size = min(max(1, page_size), 100)
    q = db.query(Payment)
    if status:
        q = q.filter(Payment.status == status)
    if provider:
        q = q.filter(Payment.provider == provider)
    total = q.count()
    rows = q.order_by(Payment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "payments": [{"id": p.id, "user_id": p.user_id, "provider": p.provider, "plan": p.plan, "amount": p.amount,
                          "currency": p.currency, "status": p.status, "external_payment_id": p.external_payment_id,
                          "error_message": p.error_message, "created_at": p.created_at.isoformat()} for p in rows]}


# ---------- AI usage ----------
@router.get("/ai-usage")
def ai_usage(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    # per-user scan counts
    rows = db.query(UsageLog.user_id, func.count(UsageLog.id)).filter(UsageLog.action == "optimize").group_by(UsageLog.user_id).all()
    user_ids = [r[0] for r in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    per_user = [{"user_id": uid, "email": users[uid].email if uid in users else None, "scans": cnt} for uid, cnt in rows]
    per_user.sort(key=lambda x: x["scans"], reverse=True)
    return {"per_user": per_user[:50]}


# ---------- Audit logs ----------
@router.get("/audit-logs")
def audit_logs(action: str = "", page: int = 1, page_size: int = 50, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = max(1, page); page_size = min(max(1, page_size), 200)
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "logs": [{"id": l.id, "actor_user_id": l.actor_user_id, "actor_role": l.actor_role, "action": l.action,
                      "target_type": l.target_type, "target_id": l.target_id, "metadata": l.metadata_json,
                      "ip_address": l.ip_address, "created_at": l.created_at.isoformat()} for l in rows]}


# ---------- System settings ----------
DEFAULT_SETTINGS = {
    "free_monthly_limit": str(FREE_MONTHLY_LIMIT),
    "premium_monthly_price": "19.00",
    "premium_annual_price": "149.00",
    "maintenance_mode": "false",
    "paddle_enabled": "true",
    "paymob_enabled": "true",
}


def _get_setting(db, key):
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if s:
        return s.value
    return DEFAULT_SETTINGS.get(key)


@router.get("/settings")
def get_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    keys = list(DEFAULT_SETTINGS.keys())
    out = {}
    for k in keys:
        out[k] = _get_setting(db, k)
    return out


class SettingIn(BaseModel):
    value: str


@router.put("/settings/{key}")
def put_setting(key: str, data: SettingIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if key not in DEFAULT_SETTINGS:
        raise HTTPException(400, "Unknown setting")
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if s:
        s.value = data.value
        s.updated_by = admin.id
    else:
        db.add(SystemSetting(key=key, value=data.value, updated_by=admin.id))
    db.commit()
    audit(db, admin, "admin.setting_change", "setting", key, metadata={"value": data.value}, ip=client_ip(request))
    return {"ok": True}


# ---------- Payment gateways status ----------
@router.get("/payment-gateways")
def payment_gateways(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from backend.config import (PADDLE_API_KEY, PADDLE_CLIENT_TOKEN, PADDLE_WEBHOOK_SECRET,
                               PADDLE_PRICE_MONTHLY, PADDLE_PRICE_ANNUAL,
                               PAYMOB_API_KEY, PAYMOB_SECRET_KEY, PAYMOB_PUBLIC_KEY,
                               PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID)
    # admin toggles
    paddle_toggle = _get_setting(db, "paddle_enabled") == "true"
    paymob_toggle = _get_setting(db, "paymob_enabled") == "true"
    paddle_configured = all([PADDLE_API_KEY, PADDLE_CLIENT_TOKEN, PADDLE_WEBHOOK_SECRET, PADDLE_PRICE_MONTHLY, PADDLE_PRICE_ANNUAL])
    paymob_configured = all([PAYMOB_API_KEY, PAYMOB_SECRET_KEY, PAYMOB_PUBLIC_KEY, PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID])
    return {
        "paddle": {"configured": paddle_configured, "enabled": paddle_toggle and paddle_configured, "environment": os.getenv("PADDLE_ENVIRONMENT", "sandbox")},
        "paymob": {"configured": paymob_configured, "enabled": paymob_toggle and paymob_configured},
    }
