"""Companies: the organisations we sell to."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.user import User


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    industry: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    # No ondelete: users are deactivated, never deleted, so an owner always exists.
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    owner: Mapped["User"] = relationship(back_populates="companies")
    # passive_deletes lets the database's ON DELETE SET NULL (on contacts.company_id)
    # unlink contacts, instead of SQLAlchemy loading and updating each one.
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<Company {self.id} {self.name}>"
