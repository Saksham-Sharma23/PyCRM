"""Shared Jinja2 template renderer."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["app_name"] = settings.app_name
