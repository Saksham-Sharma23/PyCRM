"""Home page and health check."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import DbSession
from app.core.deps import CurrentUser
from app.core.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: CurrentUser):
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/health")
def health(db: DbSession):
    """Used by the hosting platform (and us) to check the app and database are up."""
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "unavailable"
    return {"status": "ok", "database": database}
