"""Validation for the company form."""

from pydantic import Field, field_validator

from app.schemas.common import FormModel


class CompanyForm(FormModel):
    name: str = Field(max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None

    @field_validator("website")
    @classmethod
    def add_scheme(cls, value: str | None) -> str | None:
        """Accept "acme.com" and store "https://acme.com" so it works as a link."""
        if value and not value.startswith(("http://", "https://")):
            return f"https://{value}"
        return value
