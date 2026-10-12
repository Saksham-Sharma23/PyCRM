"""Companies: listing, lookup and changes, always scoped to what the user may see."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Company, User
from app.schemas.company import CompanyForm
from app.services.common import Page, escape_like, paginate, visible_to


def get_company(db: Session, user: User, company_id: int) -> Company | None:
    """Return the company, or None if it doesn't exist *or* the user may not see it."""
    stmt = visible_to(select(Company), Company, user).where(Company.id == company_id)
    return db.scalar(stmt)


def list_companies(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    industry: str | None = None,
    page: int = 1,
) -> Page[Company]:
    stmt = (
        visible_to(select(Company), Company, user)
        # Load every owner in one extra query instead of one query per row (N+1).
        .options(selectinload(Company.owner))
        .order_by(Company.name, Company.id)
    )
    if search:
        pattern = f"%{escape_like(search)}%"
        stmt = stmt.where(
            or_(
                Company.name.ilike(pattern, escape="\\"),
                Company.industry.ilike(pattern, escape="\\"),
                Company.website.ilike(pattern, escape="\\"),
            )
        )
    if industry:
        stmt = stmt.where(Company.industry == industry)
    return paginate(db, stmt, page)


def list_industries(db: Session, user: User) -> list[str]:
    """Distinct industries among the user's visible companies, for the filter dropdown."""
    stmt = (
        visible_to(select(Company.industry), Company, user)
        .where(Company.industry.is_not(None))
        .distinct()
        .order_by(Company.industry)
    )
    return list(db.scalars(stmt))


def list_company_choices(db: Session, user: User) -> list[Company]:
    """All visible companies (id + name), for the contact form's dropdown."""
    stmt = visible_to(select(Company), Company, user).order_by(Company.name)
    return list(db.scalars(stmt))


def create_company(db: Session, user: User, form: CompanyForm) -> Company:
    company = Company(**form.model_dump(), owner_id=user.id)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, company: Company, form: CompanyForm) -> Company:
    for field, value in form.model_dump().items():
        setattr(company, field, value)
    db.commit()
    return company


def delete_company(db: Session, company: Company) -> None:
    # The database's ON DELETE SET NULL unlinks this company's contacts.
    db.delete(company)
    db.commit()
