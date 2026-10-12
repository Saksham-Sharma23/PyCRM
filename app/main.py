"""Application entry point: `uvicorn app.main:app --reload`."""

from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.deps import LoginRequired
from app.core.templating import templates
from app.routers import auth, home, users

STATIC_DIR = Path(__file__).resolve().parent / "static"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # one week


def login_required_handler(request: Request, exc: LoginRequired) -> Response:
    """Send logged-out visitors to the login page, then back to where they were."""
    target = request.url.path
    if request.url.query:
        target += f"?{request.url.query}"
    login_url = f"/login?{urlencode({'next': target})}"

    # For HTMX requests a normal redirect would be swapped *into* the page,
    # so ask HTMX to do a full-page redirect instead.
    if request.headers.get("HX-Request"):
        return Response(headers={"HX-Redirect": login_url})
    return RedirectResponse(login_url, status_code=303)


def http_error_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """Show HTTP errors (403, 404, ...) as a friendly page instead of raw JSON."""
    return templates.TemplateResponse(
        request,
        "error.html",
        {"status_code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code,
    )


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # Stores the logged-in user's id in a signed cookie. The cookie can be read
    # by the browser but not changed without the secret key. SameSite=lax stops
    # other websites from sending it along with form posts (basic CSRF protection).
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="pycrm_session",
        max_age=SESSION_MAX_AGE,
        same_site="lax",
        https_only=settings.cookie_secure,
    )

    app.add_exception_handler(LoginRequired, login_required_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(home.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    return app


app = create_app()
