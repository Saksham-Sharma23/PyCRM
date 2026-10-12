"""User accounts: registration, authentication and admin management."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User, UserRole


class EmailAlreadyRegistered(Exception):
    pass


class CannotModifySelf(Exception):
    """Raised when an admin tries to demote or deactivate their own account."""


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def create_user(
    db: Session, *, name: str, email: str, password: str, role: UserRole | None = None
) -> User:
    """Create a user. If no role is given, the very first user becomes admin."""
    if get_by_email(db, email):
        raise EmailAlreadyRegistered(email)

    if role is None:
        user_count = db.scalar(select(func.count()).select_from(User))
        role = UserRole.ADMIN if user_count == 0 else UserRole.SALES_REP

    user = User(
        name=name,
        email=_normalize_email(email),
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user if the credentials are valid and the account is active."""
    user = get_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name)))


def set_role(db: Session, *, actor: User, user: User, role: UserRole) -> User:
    if user.id == actor.id:
        raise CannotModifySelf("You cannot change your own role")
    user.role = role
    db.commit()
    return user


def set_active(db: Session, *, actor: User, user: User, is_active: bool) -> User:
    if user.id == actor.id:
        raise CannotModifySelf("You cannot deactivate your own account")
    user.is_active = is_active
    db.commit()
    return user
