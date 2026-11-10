import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, account_disabled, get_current_profile
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    issued_before,
    verify_password,
)
from app.db import get_db
from app.models import Profile
from app.services import abuse
from app.schemas import ChangePasswordRequest, LoginRequest, ProfileOut, RefreshRequest, SignupRequest, TokenPair

router = APIRouter(prefix="/auth", tags=["identity"])


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    count = (await db.execute(select(func.count()).select_from(Profile))).scalar_one()
    if int(count or 0) >= 1:
        raise _problem(
            status.HTTP_403_FORBIDDEN,
            "Đăng ký đã đóng",
            "registration_closed",
            "Ứng dụng cá nhân chỉ dành cho một tài khoản duy nhất.",
        )
    key = abuse.email_key(body.email)
    profile = Profile(
        email=body.email,
        email_key=key,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        role="admin",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return TokenPair(
        access_token=create_access_token(str(profile.id), profile.role),
        refresh_token=create_refresh_token(str(profile.id), profile.role),
    )


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Profile).where(Profile.email == body.email))
    profile = result.scalar_one_or_none()
    if profile is None or not verify_password(body.password, profile.hashed_password):
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid credentials", "invalid_credentials")
    # only someone who knows the password learns the account is locked
    if profile.disabled:
        raise _problem(
            status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khoá", "account_disabled", "Liên hệ người quản trị để mở lại."
        )
    expires = profile.temp_password_expires_at
    if expires is not None and expires <= datetime.now(timezone.utc):
        raise _problem(
            status.HTTP_403_FORBIDDEN,
            "Mật khẩu tạm đã hết hạn",
            "temp_password_expired",
            "Nhờ người quản trị đặt lại mật khẩu cho bạn.",
        )
    return TokenPair(
        access_token=create_access_token(str(profile.id), profile.role),
        refresh_token=create_refresh_token(str(profile.id), profile.role),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Exchanges a still-valid refresh token for a new TokenPair.

    Access tokens are short-lived (JWT_ACCESS_TTL_MIN, currently 60 min) so
    a session doesn't stay silently authenticated forever, but until now
    there was no way to actually redeem the long-lived refresh_token that
    login/signup already hand out — apiFetch had nothing to call, so every
    session became permanently logged-out ("Invalid or expired token" on
    every request) exactly one access-token TTL after login, with no way
    back in short of logging in again. This is the missing other half of
    that flow: the frontend now calls this on a 401 invalid_token and
    retries once (see client.ts) instead of surfacing the error.

    Rotates BOTH tokens (not just re-signing a new access token) so a
    leaked refresh token has a bounded lifetime of one use, same rationale
    as the access/refresh split itself.
    """
    try:
        claims = decode_token(body.refresh_token)
    except ValueError as exc:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", "invalid_token") from exc
    if claims.get("type") != "refresh":
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", "invalid_token")
    profile = await db.get(Profile, uuid.UUID(claims["sub"]))
    if profile is None:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Profile not found", "unauthenticated")
    if profile.disabled:
        raise account_disabled()
    # a password reset / change ends every older session, refresh tokens included
    if issued_before(claims, profile.tokens_valid_after):
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", "invalid_token")
    return TokenPair(
        access_token=create_access_token(str(profile.id), profile.role),
        refresh_token=create_refresh_token(str(profile.id), profile.role),
    )


@router.get("/me", response_model=ProfileOut)
async def me(profile: Annotated[Profile, Depends(get_current_profile)]):
    return profile


@router.post("/change-password", response_model=TokenPair)
async def change_password(
    body: ChangePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The learner sets their own password (also how a temporary one from an admin is replaced).
    Every older session ends; the answer carries a fresh token pair for this one."""
    if not verify_password(body.current_password, profile.hashed_password):
        raise _problem(status.HTTP_400_BAD_REQUEST, "Mật khẩu hiện tại chưa đúng", "wrong_password")
    if body.new_password == body.current_password:
        raise _problem(status.HTTP_400_BAD_REQUEST, "Mật khẩu mới phải khác mật khẩu hiện tại", "same_password")
    profile.hashed_password = hash_password(body.new_password)
    profile.temp_password_expires_at = None
    profile.tokens_valid_after = datetime.now(timezone.utc)
    await db.commit()
    return TokenPair(
        access_token=create_access_token(str(profile.id), profile.role),
        refresh_token=create_refresh_token(str(profile.id), profile.role),
    )
