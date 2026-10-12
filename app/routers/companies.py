"""Company pages: list (with live search), detail, create, edit, delete."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.database import DbSession
from app.core.deps import CurrentUser
from app.core.forms import FormData
from app.core.templating import templates
from app.models import Company, User
from app.schemas.common import first_error_message
from app.schemas.company import CompanyForm
from app.services import company_service, contact_service

router = APIRouter(prefix="/companies")

FORM_FIELDS = list(CompanyForm.model_fields)


def _get_or_404(db: DbSession, user: User, company_id: int) -> Company:
    # Someone else's company gives 404, not 403, so we don't reveal that it exists.
    company = company_service.get_company(db, user, company_id)
    if company is None:
        raise HTTPException(404, "Company not found")
    return company


def _render_form(
    request: Request,
    user: User,
    *,
    company: Company | None = None,
    values: dict | None = None,
    error: str | None = None,
    status_code: int = 200,
):
    if values is None:
        values = {f: getattr(company, f) for f in FORM_FIELDS} if company else {}
    return templates.TemplateResponse(
        request,
        "companies/form.html",
        {"user": user, "company": company, "values": values, "error": error},
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def list_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str = "",
    industry: str = "",
    page: int = 1,
):
    q = q.strip()
    results = company_service.list_companies(
        db, user, search=q or None, industry=industry or None, page=page
    )
    # Current filters, kept in the pagination links.
    params = {key: value for key, value in {"q": q, "industry": industry}.items() if value}
    context = {"user": user, "results": results, "q": q, "industry": industry, "params": params}

    # Live search and pagination (HTMX) only need the results table, not the whole page.
    if request.headers.get("HX-Target") == "results":
        return templates.TemplateResponse(request, "partials/company_results.html", context)

    context["industries"] = company_service.list_industries(db, user)
    return templates.TemplateResponse(request, "companies/list.html", context)


# "/new" must be declared before "/{company_id}", or FastAPI would try to read
# "new" as a company id.
@router.get("/new", response_class=HTMLResponse)
def new_page(request: Request, user: CurrentUser):
    return _render_form(request, user)


@router.post("/new", response_class=HTMLResponse)
def create(request: Request, db: DbSession, user: CurrentUser, form_data: FormData):
    try:
        form = CompanyForm.model_validate(form_data)
    except ValidationError as exc:
        return _render_form(
            request, user, values=form_data, error=first_error_message(exc), status_code=400
        )
    company = company_service.create_company(db, user, form)
    # Post/Redirect/Get: refreshing the next page won't re-submit the form.
    return RedirectResponse(f"/companies/{company.id}", status_code=303)


@router.get("/{company_id}", response_class=HTMLResponse)
def detail_page(request: Request, company_id: int, db: DbSession, user: CurrentUser):
    company = _get_or_404(db, user, company_id)
    contacts = contact_service.list_contacts(db, user, company_id=company.id)
    return templates.TemplateResponse(
        request, "companies/detail.html", {"user": user, "company": company, "contacts": contacts}
    )


@router.get("/{company_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, company_id: int, db: DbSession, user: CurrentUser):
    company = _get_or_404(db, user, company_id)
    return _render_form(request, user, company=company)


@router.post("/{company_id}/edit", response_class=HTMLResponse)
def update(
    request: Request, company_id: int, db: DbSession, user: CurrentUser, form_data: FormData
):
    company = _get_or_404(db, user, company_id)
    try:
        form = CompanyForm.model_validate(form_data)
    except ValidationError as exc:
        return _render_form(
            request,
            user,
            company=company,
            values=form_data,
            error=first_error_message(exc),
            status_code=400,
        )
    company_service.update_company(db, company, form)
    return RedirectResponse(f"/companies/{company.id}", status_code=303)


@router.post("/{company_id}/delete")
def delete(company_id: int, db: DbSession, user: CurrentUser):
    company = _get_or_404(db, user, company_id)
    company_service.delete_company(db, company)
    return RedirectResponse("/companies", status_code=303)
