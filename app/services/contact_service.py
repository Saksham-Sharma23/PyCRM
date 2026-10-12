"""Contacts: listing, lookup and changes, always scoped to what the user may see."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Company, Contact, User
from app.schemas.contact import ContactForm
from app.services import company_service
from app.services.common import Page, escape_like, paginate, visible_to


class InvalidCompany(Exception):
    """The chosen company doesn't exist or isn't visible to this user."""


def get_contact(db: Session, user: User, contact_id: int) -> Contact | None:
    """Return the contact, or None if it doesn't exist *or* the user may not see it."""
    stmt = (
        visible_to(select(Contact), Contact, user)
        .options(selectinload(Contact.company), selectinload(Contact.owner))
        .where(Contact.id == contact_id)
    )
    return db.scalar(stmt)


def list_contacts(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    company_id: int | None = None,
    page: int = 1,
) -> Page[Contact]:
    stmt = (
        visible_to(select(Contact), Contact, user)
        # The list shows each contact's company and owner: load them in two
        # extra queries total, instead of two per row (the N+1 problem).
        .options(selectinload(Contact.company), selectinload(Contact.owner))
        .order_by(Contact.last_name, Contact.first_name, Contact.id)
    )
    if search:
        pattern = f"%{escape_like(search)}%"
        stmt = stmt.outerjoin(Contact.company).where(
            or_(
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
                Contact.job_title.ilike(pattern, escape="\\"),
                Company.name.ilike(pattern, escape="\\"),
            )
        )
    if company_id is not None:
        stmt = stmt.where(Contact.company_id == company_id)
    return paginate(db, stmt, page)


def _check_company(
    db: Session, user: User, company_id: int | None, current_company_id: int | None = None
) -> None:
    """Users may only link contacts to companies they can see.

    Keeping the contact's existing company is always allowed, even if an admin
    linked it to a company this user can't see.
    """
    if company_id is None or company_id == current_company_id:
        return
    if company_service.get_company(db, user, company_id) is None:
        raise InvalidCompany(company_id)


def create_contact(db: Session, user: User, form: ContactForm) -> Contact:
    _check_company(db, user, form.company_id)
    contact = Contact(**form.model_dump(), owner_id=user.id)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(db: Session, user: User, contact: Contact, form: ContactForm) -> Contact:
    _check_company(db, user, form.company_id, current_company_id=contact.company_id)
    for field, value in form.model_dump().items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: Contact) -> None:
    db.delete(contact)
    db.commit()
