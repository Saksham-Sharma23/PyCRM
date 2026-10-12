"""Query helpers shared by all services: ownership scoping and pagination."""

import math
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import User

PAGE_SIZE = 20


def visible_to(stmt: Select, model: type, user: User) -> Select:
    """Limit a query to the records this user may see.

    Admins see everything; everyone else only sees records they own. Every list
    and lookup goes through this one function, so the rule lives in one place.
    """
    if user.is_admin:
        return stmt
    return stmt.where(model.owner_id == user.id)


def escape_like(term: str) -> str:
    """Escape LIKE wildcards so a search for "50%" matches the literal text."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, math.ceil(self.total / self.page_size))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def first_item(self) -> int:
        return 0 if self.total == 0 else (self.page - 1) * self.page_size + 1

    @property
    def last_item(self) -> int:
        return min(self.page * self.page_size, self.total)


def paginate(db: Session, stmt: Select, page: int, page_size: int = PAGE_SIZE) -> Page:
    """Run `stmt` for one page of results, plus a COUNT of all matching rows."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0

    last_page = max(1, math.ceil(total / page_size))
    page = min(max(1, page), last_page)  # clamp out-of-range page numbers

    items = list(db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)))
    return Page(items=items, total=total, page=page, page_size=page_size)
