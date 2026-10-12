import pytest

from app.models import UserRole
from app.services import user_service


def signup(client, name="Ada", email="ada@example.com", password="password123"):
    return client.post(
        "/signup",
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )


# --- Protecting pages ---


def test_protected_page_redirects_to_login_with_next(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2F"


def test_htmx_request_gets_full_page_redirect_header(client):
    response = client.get("/", headers={"HX-Request": "true"}, follow_redirects=False)

    assert response.headers["HX-Redirect"] == "/login?next=%2F"


# --- Signup ---


def test_signup_logs_in_and_first_user_becomes_admin(client, db):
    response = signup(client, email="Ada@Example.com")

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    user = user_service.get_by_email(db, "ada@example.com")
    assert user.email == "ada@example.com"  # stored lowercased
    assert user.role == UserRole.ADMIN
    assert user.password_hash != "password123"
    assert "Welcome to PyCRM, Ada" in client.get("/").text


def test_later_signups_are_sales_reps(client, db, make_user):
    make_user(email="admin@example.com", role=UserRole.ADMIN)

    signup(client, name="Bob", email="bob@example.com")

    assert user_service.get_by_email(db, "bob@example.com").role == UserRole.SALES_REP


def test_signup_rejects_duplicate_email(client, make_user):
    make_user(email="alice@example.com")

    response = signup(client, email="ALICE@example.com")

    assert response.status_code == 400
    assert "already exists" in response.text


@pytest.mark.parametrize(
    ("name", "email", "password", "error_prefix"),
    [
        ("Ada", "not-an-email", "password123", "Email:"),
        ("Ada", "ada@example.com", "short", "Password:"),
        ("   ", "ada@example.com", "password123", "Name:"),
    ],
)
def test_signup_validation_errors(client, db, name, email, password, error_prefix):
    response = signup(client, name=name, email=email, password=password)

    assert response.status_code == 400
    assert error_prefix in response.text
    assert user_service.list_users(db) == []


# --- Login / logout ---


def test_login_and_logout(client, make_user, login):
    make_user(name="Alice", email="alice@example.com")

    response = login("ALICE@example.com")  # email is case-insensitive
    assert response.status_code == 303
    assert "Alice" in client.get("/").text

    client.post("/logout")
    assert client.get("/", follow_redirects=False).status_code == 303


@pytest.mark.parametrize(
    ("email", "password"),
    [("alice@example.com", "wrong-password"), ("nobody@example.com", "password123")],
)
def test_login_failure_shows_generic_error(client, make_user, login, email, password):
    make_user(email="alice@example.com")

    response = login(email, password)

    # Same message for wrong password and unknown email, so attackers
    # can't use the login form to discover which emails have accounts.
    assert response.status_code == 400
    assert "Invalid email or password" in response.text
    assert client.get("/", follow_redirects=False).status_code == 303


def test_inactive_user_cannot_log_in(db, make_user, login):
    user = make_user(email="alice@example.com")
    user.is_active = False
    db.commit()

    assert login("alice@example.com").status_code == 400


def test_login_returns_to_next_page(make_user, login):
    make_user(email="alice@example.com")

    response = login("alice@example.com", next_url="/users")

    assert response.headers["location"] == "/users"


@pytest.mark.parametrize("next_url", ["//evil.example.com", "https://evil.example.com", "/\\evil"])
def test_login_ignores_external_next_urls(make_user, login, next_url):
    make_user(email="alice@example.com")

    response = login("alice@example.com", next_url=next_url)

    assert response.headers["location"] == "/"
