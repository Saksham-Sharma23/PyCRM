import pytest

from app.models import Company


def company_form(**overrides):
    data = {"name": "Acme Inc", "industry": "", "website": "", "phone": "", "notes": ""}
    data.update(overrides)
    return data


def test_companies_require_login(client):
    assert client.get("/companies", follow_redirects=False).status_code == 303


# --- Create / edit / delete ---


def test_create_company(client, db, rep, login):
    login(rep.email)

    response = client.post(
        "/companies/new",
        data=company_form(name="  Acme Inc  ", industry="Software", website="acme.com"),
        follow_redirects=False,
    )

    assert response.status_code == 303
    company = db.get(Company, int(response.headers["location"].rsplit("/", 1)[1]))
    assert company.name == "Acme Inc"  # whitespace stripped
    assert company.owner_id == rep.id  # creator becomes the owner
    assert company.website == "https://acme.com"  # scheme added
    assert company.phone is None  # blank optional field stored as NULL


def test_create_company_requires_name(client, rep, login):
    login(rep.email)

    response = client.post("/companies/new", data=company_form(name="", industry="Software"))

    assert response.status_code == 400
    assert "Name: This field is required" in response.text
    assert 'value="Software"' in response.text  # what the user typed is kept


def test_website_cannot_be_a_javascript_link(client, db, rep, login):
    login(rep.email)

    response = client.post(
        "/companies/new", data=company_form(website="javascript:alert(1)"), follow_redirects=False
    )

    company = db.get(Company, int(response.headers["location"].rsplit("/", 1)[1]))
    assert company.website.startswith("https://")


def test_edit_company(client, db, rep, make_company, login):
    company = make_company(rep, "Acme Inc")
    login(rep.email)

    response = client.post(
        f"/companies/{company.id}/edit",
        data=company_form(name="Acme Corporation", phone="555-0100"),
        follow_redirects=False,
    )

    assert response.headers["location"] == f"/companies/{company.id}"
    db.refresh(company)
    assert company.name == "Acme Corporation"
    assert company.phone == "555-0100"


def test_edit_page_is_prefilled(client, rep, make_company, login):
    company = make_company(rep, "Acme Inc", industry="Software")
    login(rep.email)

    response = client.get(f"/companies/{company.id}/edit")

    assert 'value="Acme Inc"' in response.text
    assert 'value="Software"' in response.text


def test_delete_company_keeps_its_contacts(client, db, rep, make_company, make_contact, login):
    company = make_company(rep)
    contact = make_contact(rep, company=company)
    login(rep.email)

    response = client.post(f"/companies/{company.id}/delete", follow_redirects=False)

    assert response.headers["location"] == "/companies"
    assert db.get(Company, company.id) is None
    db.refresh(contact)
    assert contact.company_id is None  # ON DELETE SET NULL


# --- Ownership ---


def test_rep_sees_only_own_companies(client, rep, other_rep, make_company, login):
    make_company(rep, "Mine Ltd")
    make_company(other_rep, "Theirs Ltd")
    login(rep.email)

    text = client.get("/companies").text

    assert "Mine Ltd" in text
    assert "Theirs Ltd" not in text


def test_admin_sees_all_companies_with_owner(client, admin, rep, other_rep, make_company, login):
    make_company(rep, "Mine Ltd")
    make_company(other_rep, "Theirs Ltd")
    login(admin.email)

    text = client.get("/companies").text

    assert "Mine Ltd" in text and "Theirs Ltd" in text
    assert "Rex Rep" in text and "Olive Other" in text  # owner column


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", ""), ("get", "/edit"), ("post", "/edit"), ("post", "/delete")],
)
def test_other_reps_company_is_not_found(
    client, db, rep, other_rep, make_company, login, method, path
):
    company = make_company(other_rep, "Theirs Ltd")
    login(rep.email)

    response = getattr(client, method)(f"/companies/{company.id}{path}")

    assert response.status_code == 404
    assert db.get(Company, company.id) is not None


# --- Search, filter, pagination ---


@pytest.fixture
def three_companies(rep, make_company):
    make_company(rep, "Acme Inc", industry="Software")
    make_company(rep, "Globex", industry="Energy")
    make_company(rep, "Initech", industry="Software", website="https://initech.example")


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"q": "acme"}, {"Acme Inc"}),
        ({"q": "SOFT"}, {"Acme Inc", "Initech"}),  # matches industry, case-insensitive
        ({"q": "initech.example"}, {"Initech"}),  # matches website
        ({"industry": "Energy"}, {"Globex"}),
        ({"q": "acme", "industry": "Energy"}, set()),
    ],
)
def test_search_and_filter(client, rep, three_companies, login, params, expected):
    login(rep.email)

    text = client.get("/companies", params=params).text

    shown = {name for name in ("Acme Inc", "Globex", "Initech") if f">{name}</a>" in text}
    assert shown == expected


def test_search_treats_wildcards_literally(client, rep, make_company, login):
    make_company(rep, "100% Juice")
    make_company(rep, "Juicy Fruits")
    login(rep.email)

    text = client.get("/companies", params={"q": "%"}).text

    assert "100% Juice" in text
    assert "Juicy Fruits" not in text


def test_htmx_search_returns_only_the_results_table(client, rep, three_companies, login):
    login(rep.email)

    response = client.get(
        "/companies", params={"q": "acme"}, headers={"HX-Request": "true", "HX-Target": "results"}
    )

    assert "<html" not in response.text
    assert "Acme Inc" in response.text


def test_pagination(client, rep, make_company, login):
    for i in range(1, 26):
        make_company(rep, f"Company {i:02d}")
    login(rep.email)

    page_1 = client.get("/companies").text
    assert "Company 20" in page_1 and "Company 21" not in page_1
    assert "Showing 1–20 of 25" in page_1
    assert "page=2" in page_1

    page_2 = client.get("/companies", params={"page": 2}).text
    assert "Company 21" in page_2 and "Company 25" in page_2 and "Company 20" not in page_2
    assert "Showing 21–25 of 25" in page_2

    # Out-of-range pages are clamped to the last page.
    assert "Showing 21–25 of 25" in client.get("/companies", params={"page": 99}).text


def test_pagination_links_keep_the_search(client, rep, make_company, login):
    for i in range(1, 26):
        make_company(rep, f"Company {i:02d}")
    login(rep.email)

    text = client.get("/companies", params={"q": "company"}).text

    assert "q=company&amp;page=2" in text


def test_list_query_count_does_not_grow_with_rows(
    client, db, admin, make_user, make_company, login, count_queries
):
    """Guards against the N+1 problem: the owner column must not cost a query per row."""
    login(admin.email)

    def queries_for_list_page() -> int:
        db.expire_all()  # forget cached objects, as a fresh request would
        count_queries.clear()
        client.get("/companies")
        return len(count_queries)

    for i in range(3):
        make_company(make_user(name=f"Owner {i}", email=f"owner{i}@example.com"), f"Co {i}")
    few = queries_for_list_page()

    for i in range(3, 15):
        make_company(make_user(name=f"Owner {i}", email=f"owner{i}@example.com"), f"Co {i}")
    many = queries_for_list_page()

    assert many == few


# --- Detail page ---


def test_company_detail_lists_its_contacts(client, rep, make_company, make_contact, login):
    acme = make_company(rep, "Acme Inc", website="https://acme.com")
    globex = make_company(rep, "Globex")
    make_contact(rep, "Jane", "Doe", company=acme)
    make_contact(rep, "John", "Smith", company=globex)
    login(rep.email)

    text = client.get(f"/companies/{acme.id}").text

    assert "Jane Doe" in text
    assert "John Smith" not in text
    assert f"/contacts/new?company_id={acme.id}" in text  # "Add contact" preselects the company
