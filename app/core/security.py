"""JWT issuance/verification + password hashing.

Scaffold-level auth: enough to exercise role-gated endpoints
(learner/editor/admin per SDD) end to end. Swap in a proper identity
provider later if needed — nothing else in the app depends on how the
token was minted, only on the `sub` (profile id) and `role` claims.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Role = Literal["learner", "editor", "admin"]


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: Role) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MIN)
    payload = {"sub": subject, "role": role, "type": "access", "iat": now, "ts": now.timestamp(), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: Role) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    payload = {"sub": subject, "role": role, "type": "refresh", "iat": now, "ts": now.timestamp(), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid_token") from exc


def issued_before(claims: dict, cutoff: datetime | None) -> bool:
    """True when the token was issued before `cutoff` (and so must be refused). No cutoff: never.
    `ts` is the issue time to the microsecond (`iat` is whole seconds, too coarse to tell a token
    made a moment before a password change from one made a moment after). A token with no `ts`
    (made before tokens carried one) is older than any cutoff that exists."""
    if cutoff is None:
        return False
    ts = claims.get("ts")
    if not isinstance(ts, (int, float)):
        return True
    return ts < cutoff.timestamp()


TEMP_PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/l/I


def make_temporary_password(length: int = 12) -> str:
    """A random password an admin can read out or paste: no look-alike characters, ~69 bits."""
    import secrets

    return "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(length))
