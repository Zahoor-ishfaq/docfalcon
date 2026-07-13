from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain[:72], hashed)


def _make_token(
    sub: str,
    company_id: str,
    kind: Literal["access", "refresh"],
    expires_delta: timedelta,
) -> str:
    payload = {
        "sub": sub,
        "company_id": company_id,
        "kind": kind,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_access_token(sub: str, company_id: str) -> str:
    return _make_token(
        sub, company_id, "access", timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )


def create_refresh_token(sub: str, company_id: str) -> str:
    return _make_token(
        sub, company_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, expected_kind: Literal["access", "refresh"]) -> dict:
    """Raises JWTError on invalid, expired, or wrong-kind token."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("kind") != expected_kind:
        raise JWTError("wrong token kind")
    return payload