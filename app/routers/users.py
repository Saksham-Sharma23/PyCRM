"""Admin-only user management."""

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.database import DbSession
from app.core.deps import AdminUser
from app.core.templating import templates
from app.models import User, UserRole
from app.services import user_service

router = APIRouter(prefix="/users")


def _get_user_or_404(db: DbSession, user_id: int) -> User:
    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def _render_row(request: Request, admin: User, target: User):
    """Return just one table row; HTMX swaps it into the page."""
    return templates.TemplateResponse(
        request,
        "partials/user_row.html",
        {"user": admin, "u": target, "roles": list(UserRole)},
    )


@router.get("", response_class=HTMLResponse)
def users_page(request: Request, db: DbSession, admin: AdminUser):
    return templates.TemplateResponse(
        request,
        "users/list.html",
        {"user": admin, "users": user_service.list_users(db), "roles": list(UserRole)},
    )


@router.post("/{user_id}/role", response_class=HTMLResponse)
def change_role(
    request: Request,
    user_id: int,
    db: DbSession,
    admin: AdminUser,
    role: Annotated[UserRole, Form()],
):
    target = _get_user_or_404(db, user_id)
    try:
        user_service.set_role(db, actor=admin, user=target, role=role)
    except user_service.CannotModifySelf as exc:
        raise HTTPException(400, str(exc)) from exc
    return _render_row(request, admin, target)


@router.post("/{user_id}/active", response_class=HTMLResponse)
def change_active(
    request: Request,
    user_id: int,
    db: DbSession,
    admin: AdminUser,
    is_active: Annotated[bool, Form()],
):
    target = _get_user_or_404(db, user_id)
    try:
        user_service.set_active(db, actor=admin, user=target, is_active=is_active)
    except user_service.CannotModifySelf as exc:
        raise HTTPException(400, str(exc)) from exc
    return _render_row(request, admin, target)
