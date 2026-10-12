"""Auth dependencies: add `user: CurrentUser` (or `AdminUser`) to a route to protect it."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.database import DbSession
from app.models import User
from app.services import user_service

SESSION_USER_KEY = "user_id"


class LoginRequired(Exception):
    """Raised when a protected page is requested without a valid session.

    Handled in app/main.py by redirecting to the login page.
    """


def get_current_user(request: Request, db: DbSession) -> User:
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        raise LoginRequired

    user = user_service.get_by_id(db, user_id)
    if user is None or not user.is_active:
        # Account deleted or deactivated since login: end the session.
        request.session.clear()
        raise LoginRequired
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
