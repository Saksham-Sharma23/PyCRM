"""SQLAlchemy models.

Import every model module here so Base.metadata knows about all tables
(Alembic autogenerate relies on this).
"""

from app.models.base import Base, TimestampMixin
from app.models.user import User, UserRole

__all__ = ["Base", "TimestampMixin", "User", "UserRole"]
