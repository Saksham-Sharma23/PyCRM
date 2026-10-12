"""Shared test fixtures.

Tests run against a separate Postgres database (pycrm_test), never the dev one.
Override its location with the TEST_DATABASE_URL environment variable.
"""

import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.models import Base, Company, Contact, User, UserRole
from app.services import user_service

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://pycrm:pycrm@localhost:5432/pycrm_test"
)
DEFAULT_PASSWORD = "password123"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Create all tables once per test run (from the models, for speed)."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session wrapped in a transaction that is rolled back after each test.

    join_transaction_mode="create_savepoint" means the app's own db.commit()
    calls only commit a savepoint, so nothing ever really reaches the database
    and every test starts from empty tables.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """A test browser whose requests use the test session above."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def _make_user(
        name: str = "Alice",
        email: str = "alice@example.com",
        password: str = DEFAULT_PASSWORD,
        role: UserRole = UserRole.SALES_REP,
    ) -> User:
        return user_service.create_user(db, name=name, email=email, password=password, role=role)

    return _make_user


@pytest.fixture
def admin(make_user) -> User:
    return make_user(name="Ada Admin", email="admin@example.com", role=UserRole.ADMIN)


@pytest.fixture
def rep(make_user) -> User:
    return make_user(name="Rex Rep", email="rep@example.com")


@pytest.fixture
def other_rep(make_user) -> User:
    return make_user(name="Olive Other", email="other@example.com")


@pytest.fixture
def make_company(db: Session) -> Callable[..., Company]:
    def _make_company(owner: User, name: str = "Acme Inc", **fields) -> Company:
        company = Company(name=name, owner_id=owner.id, **fields)
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    return _make_company


@pytest.fixture
def make_contact(db: Session) -> Callable[..., Contact]:
    def _make_contact(
        owner: User,
        first_name: str = "Jane",
        last_name: str = "Doe",
        company: Company | None = None,
        **fields,
    ) -> Contact:
        contact = Contact(
            first_name=first_name,
            last_name=last_name,
            company_id=company.id if company else None,
            owner_id=owner.id,
            **fields,
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    return _make_contact


@pytest.fixture
def count_queries(engine: Engine) -> Iterator[list[str]]:
    """Collects every SQL statement run while the test is active."""
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    yield statements
    event.remove(engine, "before_cursor_execute", record)


@pytest.fixture
def login(client: TestClient) -> Callable[..., object]:
    def _login(email: str, password: str = DEFAULT_PASSWORD, next_url: str | None = None):
        data = {"email": email, "password": password}
        if next_url is not None:
            data["next"] = next_url
        return client.post("/login", data=data, follow_redirects=False)

    return _login
