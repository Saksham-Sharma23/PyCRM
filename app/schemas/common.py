"""Shared helpers for validating HTML form input."""

from typing import Any

from pydantic import BaseModel, ValidationError, model_validator


class FormModel(BaseModel):
    """Base for form schemas.

    HTML forms send every field as a string, and an empty input arrives as "".
    This strips whitespace and turns empty strings into None, so optional
    fields are stored as NULL and required fields fail with "is required".
    """

    @model_validator(mode="before")
    @classmethod
    def blank_strings_to_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                key: (value.strip() or None) if isinstance(value, str) else value
                for key, value in data.items()
            }
        return data


def first_error_message(error: ValidationError) -> str:
    """Turn a Pydantic error into one human-readable sentence for the form."""
    err = error.errors()[0]
    field = str(err["loc"][0]).replace("_", " ").capitalize() if err["loc"] else "Input"
    if err["type"] == "missing" or err.get("input", "") is None:
        message = "This field is required"
    else:
        message = err["msg"].removeprefix("Value error, ")
    return f"{field}: {message}"
