"""Read a whole HTML form at once, for validation with a Pydantic schema."""

from typing import Annotated

from fastapi import Depends, Request


async def get_form_data(request: Request) -> dict[str, str]:
    # Reading the body is async, so this dependency is async, while the routes
    # that use it stay plain `def` (they run in the thread pool, like our DB code).
    form = await request.form()
    return {key: value for key, value in form.items() if isinstance(value, str)}


FormData = Annotated[dict[str, str], Depends(get_form_data)]
