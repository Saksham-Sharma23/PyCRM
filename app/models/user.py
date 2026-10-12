"""User accounts: the people who log in to the CRM."""

from enum import StrEnum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserRole(StrEnum):
    ADMIN = "admin"  # sees and manages everything, including users
    SALES_REP = "sales_rep"  # sees and manages only the records they own


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Stored as plain VARCHAR ("admin"/"sales_rep") rather than a native Postgres
    # enum, so adding a role later is a simple change with no enum migration.
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]
        ),
        default=UserRole.SALES_REP,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} ({self.role})>"
