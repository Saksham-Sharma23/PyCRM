"""Contact pages: list (with live search), detail, create, edit, delete."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.database import DbSession
from app.core.deps import CurrentUser
from app.core.forms import FormData
from app.core.templating import templates
from app.models import Contact, User
from app.schemas.common import first_error_message
from app.schemas.contact import ContactForm
from app.services import company_service, contact_service

router = APIRouter(prefix="/contacts")

FORM_FIELDS = list(ContactForm.model_fields)
INVALID_COMPANY_ERROR = "Company: please choose one of your companies"


def _get_or_404(db: DbSession, user: User, contact_id: int) -> Contact:
    # Someone else's contact gives 404, not 403, so we don't reveal that it exists.
    contact = contact_service.get_contact(db, user, contact_id)
    if contact is None:
        raise HTTPException(404, "Contact not found")
    return contact


def _parse_id(value: str | None) -> int | None:
    """Query-string ids may be blank ("" from an empty <select>)."""
    return int(value) if value and value.isdigit() else None


def _render_form(
    request: Request,
    db: DbSession,
    user: User,
    *,
    contact: Contact | None = None,
    values: dict | None = None,
    error: str | None = None,
    status_code: int = 200,
):
    if values is None:
        values = {f: getattr(contact, f) for f in FORM_FIELDS} if contact else {}

    companies = company_service.list_company_choices(db, user)
    # Keep the contact's current company selectable even if this user can't see it
    # (an admin may have linked it).
    if contact and contact.company and contact.company not in companies:
        companies.append(contact.company)

    return templates.TemplateResponse(
        request,
        "contacts/form.html",
        {
            "user": user,
            "contact": contact,
            "values": values,
            "companies": companies,
            "error": error,
        },
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def list_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str = "",
    company_id: str = "",
    page: int = 1,
):
    q = q.strip()
    selected_company = _parse_id(company_id)
    results = contact_service.list_contacts(
        db, user, search=q or None, company_id=selected_company, page=page
    )
    params = {
        key: value
        for key, value in {"q": q, "company_id": selected_company}.items()
        if value not in ("", None)
    }
    context = {
        "user": user,
        "results": results,
        "q": q,
        "selected_company": selected_company,
        "params": params,
    }

    if request.headers.get("HX-Target") == "results":
        return templates.TemplateResponse(request, "partials/contact_results.html", context)

    context["companies"] = company_service.list_company_choices(db, user)
    return templates.TemplateResponse(request, "contacts/list.html", context)


@router.get("/new", response_class=HTMLResponse)
def new_page(request: Request, db: DbSession, user: CurrentUser, company_id: str = ""):
    # "Add contact" on a company page links here with ?company_id=<id> to preselect it.
    return _render_form(request, db, user, values={"company_id": _parse_id(company_id)})


@router.post("/new", response_class=HTMLResponse)
def create(request: Request, db: DbSession, user: CurrentUser, form_data: FormData):
    try:
        form = ContactForm.model_validate(form_data)
        contact = contact_service.create_contact(db, user, form)
    except ValidationError as exc:
        error = first_error_message(exc)
    except contact_service.InvalidCompany:
        error = INVALID_COMPANY_ERROR
    else:
        return RedirectResponse(f"/contacts/{contact.id}", status_code=303)

    return _render_form(request, db, user, values=form_data, error=error, status_code=400)


@router.get("/{contact_id}", response_class=HTMLResponse)
def detail_page(request: Request, contact_id: int, db: DbSession, user: CurrentUser):
    contact = _get_or_404(db, user, contact_id)
    return templates.TemplateResponse(
        request, "contacts/detail.html", {"user": user, "contact": contact}
    )


@router.get("/{contact_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, contact_id: int, db: DbSession, user: CurrentUser):
    contact = _get_or_404(db, user, contact_id)
    return _render_form(request, db, user, contact=contact)


@router.post("/{contact_id}/edit", response_class=HTMLResponse)
def update(
    request: Request, contact_id: int, db: DbSession, user: CurrentUser, form_data: FormData
):
    contact = _get_or_404(db, user, contact_id)
    try:
        form = ContactForm.model_validate(form_data)
        contact_service.update_contact(db, user, contact, form)
    except ValidationError as exc:
        error = first_error_message(exc)
    except contact_service.InvalidCompany:
        error = INVALID_COMPANY_ERROR
    else:
        return RedirectResponse(f"/contacts/{contact.id}", status_code=303)

    return _render_form(
        request, db, user, contact=contact, values=form_data, error=error, status_code=400
    )


@router.post("/{contact_id}/delete")
def delete(contact_id: int, db: DbSession, user: CurrentUser):
    contact = _get_or_404(db, user, contact_id)
    contact_service.delete_contact(db, contact)
    return RedirectResponse("/contacts", status_code=303)
