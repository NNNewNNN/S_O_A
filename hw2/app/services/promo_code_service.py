from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccessDenied,
    PromoCodeInvalid,
    PromoCodeMinAmount,
    ValidationFailed,
)
from app.crud import promo_code as promo_code_crud
from app.generated.models import (
    DiscountType as DiscountTypeDTO,
    PromoCodeResponse,
)
from db.models import (
    DiscountType as DiscountTypeORM,
    PromoCode,
    Role,
    User,
)


def _to_response(promo: PromoCode) -> PromoCodeResponse:
    discount_type_value = getattr(promo.discount_type, "value", promo.discount_type)

    return PromoCodeResponse(
        id=promo.id,
        code=promo.code,
        discount_type=DiscountTypeDTO(discount_type_value),
        discount_value=promo.discount_value,
        min_order_amount=promo.min_order_amount,
        max_uses=promo.max_uses,
        current_uses=promo.current_uses,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        active=promo.active,
    )


def _assert_can_create_promo_code(user: User) -> None:
    if user.role in {Role.SELLER, Role.ADMIN}:
        return
    raise AccessDenied()


def create_promo_code(
    db: Session,
    user: User,
    payload,
) -> PromoCodeResponse:
    _assert_can_create_promo_code(user)

    existing = promo_code_crud.get_by_code(db=db, code=payload.code)
    if existing is not None:
        raise ValidationFailed(
            details={
                "fields": [
                    {
                        "field": "code",
                        "message": "Promo code with this code already exists",
                    }
                ]
            }
        )

    valid_from = payload.valid_from
    valid_until = payload.valid_until

    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=timezone.utc)
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)

    if valid_until <= valid_from:
        raise ValidationFailed(
            details={
                "fields": [
                    {
                        "field": "valid_until",
                        "message": "valid_until must be after valid_from",
                    }
                ]
            }
        )

    discount_type_value = getattr(
        payload.discount_type,
        "value",
        payload.discount_type,
    )

    promo_code = promo_code_crud.create_promo_code(
        db=db,
        code=payload.code,
        discount_type=DiscountTypeORM(discount_type_value),
        discount_value=payload.discount_value,
        min_order_amount=payload.min_order_amount,
        max_uses=payload.max_uses,
        valid_from=valid_from,
        valid_until=valid_until,
        active=payload.active if payload.active is not None else True,
    )

    db.commit()
    db.refresh(promo_code)

    return _to_response(promo_code)


def validate_and_apply_promo_code(
    db: Session,
    promo_code_str: str,
    total_amount: Decimal,
) -> Tuple[Optional[PromoCode], Decimal]:

    if not promo_code_str:
        return None, Decimal("0")

    promo_code = promo_code_crud.get_by_code(db=db, code=promo_code_str)

    if promo_code is None:
        raise PromoCodeInvalid()

    if not promo_code.active:
        raise PromoCodeInvalid()

    now = datetime.now(timezone.utc)

    valid_from = promo_code.valid_from
    valid_until = promo_code.valid_until

    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=timezone.utc)
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)

    if now < valid_from or now > valid_until:
        raise PromoCodeInvalid()

    if promo_code.current_uses >= promo_code.max_uses:
        raise PromoCodeInvalid()

    if total_amount < promo_code.min_order_amount:
        raise PromoCodeMinAmount()

    discount_amount = calculate_discount(
        promo_code=promo_code,
        total_amount=total_amount,
    )

    return promo_code, discount_amount


def calculate_discount(
    promo_code: PromoCode,
    total_amount: Decimal,
) -> Decimal:
    discount_type_value = getattr(
        promo_code.discount_type,
        "value",
        promo_code.discount_type,
    )

    if discount_type_value == DiscountTypeORM.PERCENTAGE.value:
        discount = total_amount * promo_code.discount_value / Decimal("100")
        max_discount = total_amount * Decimal("0.70")
        if discount > max_discount:
            discount = max_discount
        return discount

    elif discount_type_value == DiscountTypeORM.FIXED_AMOUNT.value:
        return min(promo_code.discount_value, total_amount)

    return Decimal("0")