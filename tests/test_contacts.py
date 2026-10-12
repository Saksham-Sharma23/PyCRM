import pytest

from app.models import Contact


def contact_form(**overrides):
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "",
        "phone": "",
        "job_title": "",
        "notes": "",
        "company_id": "",
    }
    data.update(overrides)
    return data


def created_contact(db, response) -> Contact:
    return db.get(Contact, int(response.headers["location"].rsplit("/", 1)[1]))


def test_contacts_require_login(client):
    assert client.get("/contacts", follow_redirects=False).status_code == 303


# --- Create ---


def test_create_contact_at_a_company(client, db, rep, make_company, login):
    company = make_company(rep)
    login(rep.email)

    response = client.post(
        "/contacts/new",
        data=contact_form(email="jane@acme.com", job_title="CTO", company_id=str(company.id)),
        follow_redirects=False,
    )

    assert response.status_code == 303
    contact = created_contact(db, response)
    assert contact.full_name == "Jane Doe"
    assert contact.company_id == company.id
    assert contact.owner_id == rep.id


def test_create_contact_without_company(client, db, rep, login):
    login(rep.email)

    response = client.post("/contacts/new", data=contact_form(), follow_redirects=False)

    contact = created_contact(db, response)
    assert contact.company_id is None
    assert contact.email is None


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"first_name": ""}, "First name: This field is required"),
        ({"last_name": "   "}, "Last name: This field is required"),
        ({"email": "not-an-email"}, "Email:"),
    ],
)
def test_create_contact_validation(client, db, rep, login, overrides, error):
    login(rep.email)

    response = client.post("/contacts/new", data=contact_form(**overrides))

    assert response.status_code == 400
    assert error in response.text


def test_cannot_link_contact_to_another_reps_company(
    client, db, rep, other_rep, make_company, login
):
    theirs = make_company(other_rep, "Theirs Ltd")
    login(rep.email)

    response = client.post("/contacts/new", data=contact_form(company_id=str(theirs.id)))

    assert response.status_code == 400
    assert "please choose one of your companies" in response.text
    assert db.query(Contact).count() == 0


def test_cannot_link_contact_to_missing_company(client, rep, login):
    login(rep.email)

    response = client.post("/contacts/new", data=contact_form(company_id="99999"))

    assert response.status_code == 400


def test_new_contact_form_preselects_company(client, rep, make_company, login):
    company = make_company(rep, "Acme Inc")
    login(rep.email)

    text = client.get("/contacts/new", params={"company_id": company.id}).text

    assert f'<option value="{company.id}" selected>Acme Inc</option>' in text


def test_company_dropdown_only_offers_own_companies(client, rep, other_rep, make_company, login):
    make_company(rep, "Mine Ltd")
    make_company(other_rep, "Theirs Ltd")
    login(rep.email)

    text = client.get("/contacts/new").text

    assert "Mine Ltd" in text
    assert "Theirs Ltd" not in text


# --- Edit / delete ---


def test_edit_contact(client, db, rep, make_company, make_contact, login):
    contact = make_contact(rep)
    company = make_company(rep)
    login(rep.email)

    response = client.post(
        f"/contacts/{contact.id}/edit",
        data=contact_form(job_title="VP Sales", company_id=str(company.id)),
        follow_redirects=False,
    )

    assert response.headers["location"] == f"/contacts/{contact.id}"
    db.refresh(contact)
    assert contact.job_title == "VP Sales"
    assert contact.company_id == company.id


def test_edit_keeps_a_company_the_rep_cannot_see(
    client, db, rep, other_rep, make_company, make_contact, login
):
    # e.g. an admin linked the rep's contact to another rep's company
    theirs = make_company(other_rep, "Theirs Ltd")
    contact = make_contact(rep, company=theirs)
    login(rep.email)

    assert "Theirs Ltd" in client.get(f"/contacts/{contact.id}/edit").text
    response = client.post(
        f"/contacts/{contact.id}/edit",
        data=contact_form(job_title="Buyer", company_id=str(theirs.id)),
        follow_redirects=False,
    )

    assert response.status_code == 303
    db.refresh(contact)
    assert contact.company_id == theirs.id


def test_delete_contact(client, db, rep, make_contact, login):
    contact = make_contact(rep)
    login(rep.email)

    response = client.post(f"/contacts/{contact.id}/delete", follow_redirects=False)

    assert response.headers["location"] == "/contacts"
    assert db.get(Contact, contact.id) is None


# --- Ownership ---


def test_rep_sees_only_own_contacts(client, rep, other_rep, make_contact, login):
    make_contact(rep, "Mine", "Person")
    make_contact(other_rep, "Their", "Person")
    login(rep.email)

    text = client.get("/contacts").text

    assert "Mine Person" in text
    assert "Their Person" not in text


def test_admin_sees_all_contacts(client, admin, rep, other_rep, make_contact, login):
    make_contact(rep, "Mine", "Person")
    make_contact(other_rep, "Their", "Person")
    login(admin.email)

    text = client.get("/contacts").text

    assert "Mine Person" in text and "Their Person" in text


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", ""), ("get", "/edit"), ("post", "/edit"), ("post", "/delete")],
)
def test_other_reps_contact_is_not_found(
    client, db, rep, other_rep, make_contact, login, method, path
):
    contact = make_contact(other_rep)
    login(rep.email)

    response = getattr(client, method)(f"/contacts/{contact.id}{path}")

    assert response.status_code == 404
    assert db.get(Contact, contact.id) is not None


# --- Search and filter ---


@pytest.fixture
def people(rep, make_company, make_contact):
    acme = make_company(rep, "Acme Inc")
    globex = make_company(rep, "Globex")
    make_contact(rep, "Jane", "Doe", company=acme, email="jane@acme.com")
    make_contact(rep, "John", "Smith", company=globex, job_title="Engineer")
    make_contact(rep, "Mary", "Major")
    return {"acme": acme, "globex": globex}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("doe", {"Jane Doe"}),
        ("JANE@ACME", {"Jane Doe"}),  # email, case-insensitive
        ("engineer", {"John Smith"}),  # job title
        ("globex", {"John Smith"}),  # company name
        ("m", {"Jane Doe", "John Smith", "Mary Major"}),
    ],
)
def test_search_contacts(client, rep, people, login, query, expected):
    login(rep.email)

    text = client.get("/contacts", params={"q": query}).text

    shown = {name for name in ("Jane Doe", "John Smith", "Mary Major") if f">{name}</a>" in text}
    assert shown == expected


def test_filter_contacts_by_company(client, rep, people, login):
    login(rep.email)

    text = client.get("/contacts", params={"company_id": people["acme"].id}).text

    assert ">Jane Doe</a>" in text
    assert ">John Smith</a>" not in text


def test_blank_company_filter_shows_everyone(client, rep, people, login):
    login(rep.email)

    text = client.get("/contacts", params={"company_id": ""}).text

    assert ">Jane Doe</a>" in text and ">Mary Major</a>" in text


def test_contact_list_query_count_does_not_grow_with_rows(
    client, db, admin, make_user, make_company, make_contact, login, count_queries
):
    """Guards against N+1: company and owner columns must not cost queries per row."""
    login(admin.email)

    def queries_for_list_page() -> int:
        db.expire_all()
        count_queries.clear()
        client.get("/contacts")
        return len(count_queries)

    def add_contacts(start: int, stop: int) -> None:
        for i in range(start, stop):
            owner = make_user(name=f"Owner {i}", email=f"owner{i}@example.com")
            make_contact(owner, "Person", str(i), company=make_company(owner, f"Co {i}"))

    add_contacts(0, 3)
    few = queries_for_list_page()
    add_contacts(3, 15)
    many = queries_for_list_page()

    assert many == few
