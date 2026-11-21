import hashlib
import secrets
import jwt
import pyotp
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, PasswordResetToken, EmailVerificationToken, Resume, Optimization, JobDescription
from backend.config import APP_BASE_URL, JWT_SECRET, JWT_ALGORITHM
from backend.services.email_validation.email_validator import validate_email
from backend.auth import hash_password, verify_password, create_token
from backend.deps import get_current_user, audit, client_ip
from backend.rate_limit import limiter
from backend.config import RATE_LIMIT_AUTH

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


def _user_out(u: User, token: str):
    return {"id": u.id, "email": u.email, "name": u.name, "plan": u.plan, "token": token}


@router.post("/register")
@limiter.limit(RATE_LIMIT_AUTH)
def register(request: Request, data: RegisterIn, db: Session = Depends(get_db)):
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    vr = validate_email(data.email, check_mx=True)
    if vr.status in ("invalid_email", "invalid_domain", "disposable_domain"):
        raise HTTPException(400, vr.message)
    email = vr.email
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    u = User(email=email, password_hash=hash_password(data.password), name=data.name.strip()[:120],
             account_type="individual", email_verified=False)
    db.add(u)
    db.commit()
    db.refresh(u)
    audit(db, u, "user.register", "user", u.id, ip=client_ip(request))
    token = create_token(u.id, u.email)
    return _user_out(u, token)


@router.post("/login")
@limiter.limit(RATE_LIMIT_AUTH)
def login(request: Request, data: LoginIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    u = db.query(User).filter(User.email == email).first()
    if not u or not verify_password(data.password, u.password_hash):
        audit(db, None, "user.login_failed", "user", None, metadata={"email": email}, ip=client_ip(request))
        raise HTTPException(401, "Invalid email or password")
    if u.is_suspended:
        raise HTTPException(403, "Account suspended")
    if u.mfa_enabled:
        # issue a short-lived MFA token
        mfa_token = create_token(u.id, u.email) + ".mfa"
        # store a marker by reusing JWT with a short expiry via a separate lightweight token
        import jwt as _jwt
        mfa_payload = {"sub": str(u.id), "scope": "mfa", "exp": datetime.utcnow() + timedelta(minutes=5)}
        mfa_tok = _jwt.encode(mfa_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"mfa_required": True, "mfa_token": mfa_tok, "email": u.email}
    u.last_login_at = datetime.utcnow()
    db.commit()
    audit(db, u, "user.login", "user", u.id, ip=client_ip(request))
    token = create_token(u.id, u.email)
    return _user_out(u, token)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "plan": user.plan, "role": user.role, "email_verified": user.email_verified, "account_type": user.account_type}


@router.get("/account/export")
def export_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resumes = db.query(Resume).filter(Resume.user_id == user.id).all()
    opts = db.query(Optimization).filter(Optimization.user_id == user.id).all()
    jds = db.query(JobDescription).filter(JobDescription.user_id == user.id).all()
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name, "plan": user.plan, "created_at": user.created_at.isoformat()},
        "resumes": [{"id": r.id, "title": r.title, "content": r.content, "created_at": r.created_at.isoformat()} for r in resumes],
        "job_descriptions": [{"id": j.id, "title": j.title, "content": j.content, "created_at": j.created_at.isoformat()} for j in jds],
        "optimizations": [{"id": o.id, "ats_score": o.ats_score, "analysis": o.analysis, "tailored_resume": o.tailored_resume,
                           "cover_letter": o.cover_letter, "created_at": o.created_at.isoformat()} for o in opts],
    }


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # cascade delete via ORM relationships
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "Account deleted."}


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    token: str
    new_password: str


class VerifyIn(BaseModel):
    token: str


def _hash_token(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, data: ForgotIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    u = db.query(User).filter(User.email == email).first()
    # Always respond success to avoid email enumeration
    if u:
        raw = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(user_id=u.id, token_hash=_hash_token(raw), expires_at=datetime.utcnow() + timedelta(hours=1)))
        db.commit()
        link = f"{APP_BASE_URL}/?reset_token={raw}"
        # Dev-mode: log link (in production, send via SMTP)
        print(f"[password-reset] {email}: {link}")
    sent = False
    try:
        from backend.services.email_service import send_password_reset_email, is_configured
        if is_configured():
            sent = send_password_reset_email(email, link)
    except Exception:
        pass
    resp = {"ok": True, "message": "If the email exists, a reset link has been sent."}
    if not sent:
        resp["dev_link"] = link
    return resp


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, data: ResetIn, db: Session = Depends(get_db)):
    if len(data.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    th = _hash_token(data.token)
    rec = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == th, PasswordResetToken.used == False).first()
    if not rec or rec.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired token")
    u = db.query(User).filter(User.id == rec.user_id).first()
    if not u:
        raise HTTPException(400, "Invalid token")
    u.password_hash = hash_password(data.new_password)
    rec.used = True
    db.commit()
    return {"ok": True, "message": "Password updated."}


@router.post("/request-verification")
def request_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email_verified:
        return {"ok": True, "message": "Already verified."}
    raw = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(user_id=user.id, token_hash=_hash_token(raw), expires_at=datetime.utcnow() + timedelta(hours=24)))
    db.commit()
    link = f"{APP_BASE_URL}/?verify_token={raw}"
    print(f"[email-verify] {user.email}: {link}")
    sent = False
    try:
        from backend.services.email_service import send_verification_email, is_configured
        if is_configured():
            sent = send_verification_email(user.email, link)
    except Exception:
        pass
    resp = {"ok": True, "message": "Verification link sent."}
    if not sent:
        resp["dev_link"] = link
    return resp


@router.post("/verify-email")
@limiter.limit("10/minute")
def verify_email(request: Request, data: VerifyIn, db: Session = Depends(get_db)):
    th = _hash_token(data.token)
    rec = db.query(EmailVerificationToken).filter(EmailVerificationToken.token_hash == th, EmailVerificationToken.used == False).first()
    if not rec or rec.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired token")
    u = db.query(User).filter(User.id == rec.user_id).first()
    if not u:
        raise HTTPException(400, "Invalid token")
    u.email_verified = True
    rec.used = True
    db.commit()
    return {"ok": True, "message": "Email verified."}


# ---------- MFA (TOTP) ----------
class MfaCodeIn(BaseModel):
    code: str


class MfaCompleteIn(BaseModel):
    mfa_token: str
    code: str


@router.post("/mfa/setup")
def mfa_setup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    user.mfa_enabled = False
    db.commit()
    return {"secret": secret, "otpauth_uri": pyotp.totp.TOTP(secret).provisioning_uri(name=user.email or user.username or "user", issuer_name="ResumeForge AI")}


@router.post("/mfa/verify")
def mfa_verify(data: MfaCodeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.mfa_secret:
        raise HTTPException(400, "MFA not set up")
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(400, "Invalid code")
    user.mfa_enabled = True
    db.commit()
    return {"ok": True, "message": "MFA enabled."}


@router.post("/mfa/disable")
def mfa_disable(data: MfaCodeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.mfa_enabled:
        raise HTTPException(400, "MFA not enabled")
    if not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(data.code, valid_window=1):
        raise HTTPException(400, "Invalid code")
    user.mfa_enabled = False
    user.mfa_secret = None
    db.commit()
    return {"ok": True, "message": "MFA disabled."}


@router.post("/mfa/complete")
def mfa_complete(data: MfaCompleteIn, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.mfa_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(401, "Invalid or expired MFA token")
    if payload.get("scope") != "mfa":
        raise HTTPException(401, "Invalid MFA token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(401, "Invalid MFA state")
    if not pyotp.TOTP(user.mfa_secret).verify(data.code, valid_window=1):
        raise HTTPException(400, "Invalid code")
    user.last_login_at = datetime.utcnow()
    db.commit()
    token = create_token(user.id, user.email or user.username)
    return _user_out(user, token)
