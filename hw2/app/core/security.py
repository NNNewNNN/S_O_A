import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

import bcrypt
import jwt

from app.core.exceptions import (
    RefreshTokenInvalid,
    TokenExpired,
    TokenInvalid,
)

from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-change-me",
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(
    subject: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = _now()

    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_access_token(user_id: UUID, role: str) -> str:
    return _create_token(
        subject=str(user_id),
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: UUID, role: str) -> str:
    return _create_token(
        subject=str(user_id),
        role=role,
        token_type="refresh",
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpired()
    except jwt.InvalidTokenError:
        raise TokenInvalid()

    if payload.get("type") != "access":
        raise TokenInvalid()

    return payload


def decode_refresh_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except jwt.InvalidTokenError:
        raise RefreshTokenInvalid()

    if payload.get("type") != "refresh":
        raise RefreshTokenInvalid()

    return payload