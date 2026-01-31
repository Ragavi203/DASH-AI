from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from typing import Any

import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LoginCode, User


def request_login_code(db: Session, email: str) -> dict[str, Any]:
    """
    Creates a short-lived login code. In dev we return the code for convenience.
    In prod you'd email it.
    """
    settings = get_settings()
    email_n = normalize_email(email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = _sha256(email_n + ":" + code)
    # NOTE: SQLite returns naive datetimes even with timezone=True columns.
    # Use naive UTC consistently to avoid "offset-naive and offset-aware" comparisons.
    now = dt.datetime.utcnow()
    exp = now + dt.timedelta(minutes=10)

    # invalidate old codes
    db.query(LoginCode).filter(LoginCode.email == email_n).delete()
    db.add(LoginCode(email=email_n, code_hash=code_hash, expires_at=exp))
    db.commit()

    out: dict[str, Any] = {"ok": True}
    if settings.app_env == "dev":
        out["dev_code"] = code
    return out


def verify_login_code(db: Session, email: str, code: str) -> dict[str, Any]:
    settings = get_settings()
    email_n = normalize_email(email)
    code = str(code).strip()

    row = db.query(LoginCode).filter(LoginCode.email == email_n).first()
    if not row:
        raise ValueError("No code requested for this email")
    now = dt.datetime.utcnow()
    expires_at = row.expires_at
    if isinstance(expires_at, dt.datetime) and expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    if expires_at and expires_at < now:
        raise ValueError("Code expired")
    if row.code_hash != _sha256(email_n + ":" + code):
        raise ValueError("Invalid code")

    user = db.query(User).filter(User.email == email_n).first()
    if not user:
        user = User(email=email_n)
        db.add(user)
        db.commit()
        db.refresh(user)

    # one-time use
    db.query(LoginCode).filter(LoginCode.email == email_n).delete()
    db.commit()

    token = _mint_jwt(user_id=int(user.id), email=user.email)
    return {"access_token": token, "token_type": "bearer", "user": {"id": int(user.id), "email": user.email}}


def decode_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def _mint_jwt(user_id: int, email: str) -> str:
    settings = get_settings()
    # IMPORTANT: Use timezone-aware UTC for JWT timestamps.
    # Naive datetimes may be interpreted as local time when converted to epoch, producing "iat in the future".
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(minutes=int(settings.jwt_exp_minutes))
    payload = {"sub": str(user_id), "email": email, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

