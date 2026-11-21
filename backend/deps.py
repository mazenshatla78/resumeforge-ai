from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, AuditLog
from backend.auth import decode_token
from backend.config import JWT_SECRET
import jwt


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token payload")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(401, "User not found")
    if user.is_suspended:
        raise HTTPException(403, "Account suspended")
    return user


def get_optional_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return get_current_user(authorization, db)
    except Exception:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def audit(db: Session, actor: User | None, action: str, target_type: str = None, target_id: str = None,
          metadata: dict = None, ip: str = None, role: str = None):
    try:
        entry = AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_role=role or (actor.role if actor else "system"),
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            metadata_json=metadata or {},
            ip_address=ip,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()


def client_ip(request: Request) -> str:
    # Trust proxy header if present
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""
