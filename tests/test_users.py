from fastapi.testclient import TestClient

from app.main import app
from app.models import UserRole


def test_sales_rep_cannot_open_users_page(client, make_user, login):
    make_user(email="rep@example.com", role=UserRole.SALES_REP)
    login("rep@example.com")

    response = client.get("/users")

    assert response.status_code == 403
    assert "Admins only" in response.text


def test_admin_sees_all_users(client, make_user, login):
    make_user(name="Admin", email="admin@example.com", role=UserRole.ADMIN)
    make_user(name="Rep", email="rep@example.com")
    login("admin@example.com")

    response = client.get("/users")

    assert response.status_code == 200
    assert "admin@example.com" in response.text
    assert "rep@example.com" in response.text


def test_admin_changes_role_and_gets_updated_row(client, db, make_user, login):
    make_user(email="admin@example.com", role=UserRole.ADMIN)
    rep = make_user(email="rep@example.com")
    login("admin@example.com")

    response = client.post(f"/users/{rep.id}/role", data={"role": "admin"})

    assert response.status_code == 200
    assert f'id="user-{rep.id}"' in response.text
    assert "<html" not in response.text  # only the row, for HTMX to swap in
    db.refresh(rep)
    assert rep.role == UserRole.ADMIN


def test_deactivated_user_is_logged_out(client, db, make_user, login):
    make_user(email="admin@example.com", role=UserRole.ADMIN)
    rep = make_user(email="rep@example.com")

    with TestClient(app) as rep_client:
        rep_client.post("/login", data={"email": "rep@example.com", "password": "password123"})
        assert rep_client.get("/", follow_redirects=False).status_code == 200

        login("admin@example.com")
        client.post(f"/users/{rep.id}/active", data={"is_active": "false"})

        db.refresh(rep)
        assert rep.is_active is False
        assert rep_client.get("/", follow_redirects=False).status_code == 303


def test_admin_cannot_demote_or_deactivate_self(client, db, make_user, login):
    admin = make_user(email="admin@example.com", role=UserRole.ADMIN)
    login("admin@example.com")

    assert client.post(f"/users/{admin.id}/role", data={"role": "sales_rep"}).status_code == 400
    assert client.post(f"/users/{admin.id}/active", data={"is_active": "false"}).status_code == 400
    db.refresh(admin)
    assert admin.role == UserRole.ADMIN
    assert admin.is_active is True


def test_unknown_user_returns_404(client, make_user, login):
    make_user(email="admin@example.com", role=UserRole.ADMIN)
    login("admin@example.com")

    assert client.post("/users/99999/role", data={"role": "admin"}).status_code == 404
