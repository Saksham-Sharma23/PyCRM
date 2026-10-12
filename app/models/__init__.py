"""SQLAlchemy models.

Import every model module here so Base.metadata knows about all tables
(Alembic autogenerate relies on this).
"""

from app.models.base import Base, TimestampMixin
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User, UserRole

__all__ = ["Base", "Company", "Contact", "TimestampMixin", "User", "UserRole"]
