from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import PromoCode


def get_by_code(db: Session, code: str) -> Optional[PromoCode]:
    return db.query(PromoCode).filter(PromoCode.code == code).first()


def get_by_id(db: Session, promo_code_id: UUID) -> Optional[PromoCode]:
    return db.get(PromoCode, promo_code_id)


def create_promo_code(
    db: Session,
    code: str,
    discount_type,
    discount_value,
    min_order_amount,
    max_uses: int,
    valid_from,
    valid_until,
    active: bool = True,
) -> PromoCode:
    promo_code = PromoCode(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        min_order_amount=min_order_amount,
        max_uses=max_uses,
        current_uses=0,
        valid_from=valid_from,
        valid_until=valid_until,
        active=active,
    )
    db.add(promo_code)
    db.flush()
    return promo_code


def increment_uses(db: Session, promo_code: PromoCode) -> None:
    promo_code.current_uses += 1


def decrement_uses(db: Session, promo_code: PromoCode) -> None:
    if promo_code.current_uses > 0:
        promo_code.current_uses -= 1