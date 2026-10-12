from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


class FakeSession:
    """Stands in for a real DB session to simulate the database being up or down."""

    def __init__(self, fail: bool = False):
        self.fail = fail

    def execute(self, statement):
        if self.fail:
            raise OperationalError(str(statement), {}, Exception("connection refused"))


def test_home_page_greets_logged_in_user(client, make_user, login):
    make_user(name="Alice", email="alice@example.com")
    login("alice@example.com")

    response = client.get("/")

    assert response.status_code == 200
    assert "Welcome to PyCRM, Alice" in response.text


def test_health_ok_when_database_reachable(client):
    app.dependency_overrides[get_db] = lambda: FakeSession()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_database_unavailable(client):
    app.dependency_overrides[get_db] = lambda: FakeSession(fail=True)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "unavailable"}
