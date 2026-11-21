import bcrypt
import jwt
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

_ph = PasswordHasher()  # Argon2id by default


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    # Argon2id
    if hashed.startswith("$argon2"):
        try:
            _ph.verify(hashed, password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    # Legacy bcrypt
    if hashed.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    return False


def needs_rehash(hashed: str) -> bool:
    if hashed.startswith("$argon2"):
        try:
            return _ph.check_needs_rehash(hashed)
        except Exception:
            return False
    return True  # bcrypt -> upgrade
