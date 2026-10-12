"""Signup, login and logout."""

from typing import Annotated

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.database import DbSession
from app.core.deps import SESSION_USER_KEY
from app.core.templating import templates
from app.models import User
from app.schemas.common import first_error_message
from app.schemas.user import SignupForm
from app.services import user_service

router = APIRouter()


def _safe_next(next_url: str | None) -> str:
    """Only allow redirects to paths on this site (prevents open-redirect attacks)."""
    if next_url and next_url.startswith("/") and not next_url.startswith(("//", "/\\")):
        return next_url
    return "/"


def _start_session(request: Request, user: User) -> None:
    # Clear first so no data from a previous session carries over.
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next_url: Annotated[str, Query(alias="next")] = "/"):
    if request.session.get(SESSION_USER_KEY):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"next": _safe_next(next_url)})


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    db: DbSession,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next_url: Annotated[str, Form(alias="next")] = "/",
):
    user = user_service.authenticate(db, email, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid email or password", "email": email, "next": _safe_next(next_url)},
            status_code=400,
        )
    _start_session(request, user)
    return RedirectResponse(_safe_next(next_url), status_code=303)


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    if request.session.get(SESSION_USER_KEY):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/signup.html")


@router.post("/signup", response_class=HTMLResponse)
def signup(
    request: Request,
    db: DbSession,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    form_values = {"name": name, "email": email}
    try:
        form = SignupForm(name=name, email=email, password=password)
        user = user_service.create_user(
            db, name=form.name, email=form.email, password=form.password
        )
    except ValidationError as exc:
        error = first_error_message(exc)
    except user_service.EmailAlreadyRegistered:
        error = "An account with this email already exists"
    else:
        _start_session(request, user)
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request, "auth/signup.html", {"error": error, **form_values}, status_code=400
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
