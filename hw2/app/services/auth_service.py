from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import (
    InvalidCredentials,
    RefreshTokenInvalid,
    ValidationFailed,
)
from app.crud import user as user_crud
from app.generated.models import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokensResponse,
)
from db.models import Role as RoleORM, User


def register_user(
    db: Session,
    payload: AuthRegisterRequest,
) -> User:
    existing_user = user_crud.get_by_username(
        db=db,
        username=payload.username,
    )

    if existing_user:
        raise ValidationFailed(
            details={
                "fields": [
                    {
                        "field": "username",
                        "message": "Username already exists",
                    }
                ]
            }
        )

    password_hash = security.hash_password(payload.password.get_secret_value())
    role_value = getattr(payload.role, "value", payload.role)

    if role_value is None:
        role_value = RoleORM.USER.value

    role = RoleORM(role_value)

    try:
        user = user_crud.create_user(
            db=db,
            username=payload.username,
            password_hash=password_hash,
            role=role,
        )
    except IntegrityError:
        db.rollback()
        raise ValidationFailed(
            details={
                "fields": [
                    {
                        "field": "username",
                        "message": "Username already exists",
                    }
                ]
            }
        )

    return user


def authenticate_user(
    db: Session,
    payload: AuthLoginRequest,
) -> User:
    user = user_crud.get_by_username(
        db=db,
        username=payload.username,
    )

    if user is None:
        raise InvalidCredentials()

    if not security.verify_password(payload.password.get_secret_value(), user.password_hash):
        raise InvalidCredentials()

    return user


def _tokens_response(user: User) -> AuthTokensResponse:
    access_token = security.create_access_token(
        user_id=user.id,
        role=user.role.value,
    )

    refresh_token = security.create_refresh_token(
        user_id=user.id,
        role=user.role.value,
    )

    return AuthTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=security.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def login(
    db: Session,
    payload: AuthLoginRequest,
) -> AuthTokensResponse:
    user = authenticate_user(
        db=db,
        payload=payload,
    )

    return _tokens_response(user)


def refresh_tokens(
    db: Session,
    payload: AuthRefreshRequest,
) -> AuthTokensResponse:
    data = security.decode_refresh_token(payload.refresh_token)

    try:
        user_id = UUID(data.get("sub"))
    except (TypeError, ValueError):
        raise RefreshTokenInvalid()

    user = user_crud.get_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise RefreshTokenInvalid()

    return _tokens_response(user)