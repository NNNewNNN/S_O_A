from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import TokenInvalid
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from db.models import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise TokenInvalid()

    payload = decode_access_token(credentials.credentials)

    try:
        user_id = UUID(payload.get("sub"))
    except (TypeError, ValueError):
        raise TokenInvalid()

    user = db.get(User, user_id)

    if user is None:
        raise TokenInvalid()

    if payload.get("role") != user.role.value:
        raise TokenInvalid()

    return user