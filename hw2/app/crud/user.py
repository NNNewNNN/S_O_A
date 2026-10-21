from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import Role, User


def get_by_username(
    db: Session,
    username: str,
) -> Optional[User]:
    return (
        db.query(User)
        .filter(User.username == username)
        .first()
    )


def get_by_id(
    db: Session,
    user_id: UUID,
) -> Optional[User]:
    return db.get(User, user_id)


def create_user(
    db: Session,
    username: str,
    password_hash: str,
    role: Role,
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user