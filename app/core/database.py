"""Database engine and per-request session dependency."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# pool_pre_ping checks a connection is alive before using it (avoids errors
# after the database restarts or a hosted DB closes idle connections).
# connect_timeout makes requests fail fast instead of hanging if the DB is down.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with SessionLocal() as db:
        yield db


# Use as a route parameter type: `def view(db: DbSession): ...`
DbSession = Annotated[Session, Depends(get_db)]
