"""Validation for user-related form input."""

from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator

from app.core.security import MAX_PASSWORD_BYTES


class SignupForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


def first_error_message(error: ValidationError) -> str:
    """Turn a Pydantic error into one human-readable sentence for the form."""
    err = error.errors()[0]
    field = str(err["loc"][0]).capitalize() if err["loc"] else "Input"
    message = err["msg"].removeprefix("Value error, ")
    return f"{field}: {message}"
