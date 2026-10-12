"""Validation for the contact form."""

from pydantic import EmailStr, Field

from app.schemas.common import FormModel


class ContactForm(FormModel):
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    company_id: int | None = None  # chosen from a dropdown; blank means "no company"
