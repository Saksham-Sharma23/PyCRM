# PyCRM — Learning Notes

My revision notes from building PyCRM. Each topic has the key ideas plus a short **interview answer** to practise saying out loud.

## Contents
1. [Choosing the stack: FastAPI vs Django](#1-choosing-the-stack-fastapi-vs-django)
2. [Project architecture](#2-project-architecture)
3. [Uvicorn and ASGI](#3-uvicorn-and-asgi)
4. [How a request flows through the app](#4-how-a-request-flows-through-the-app)
5. [PostgreSQL and the database URL](#5-postgresql-and-the-database-url)
6. [Settings and the .env file](#6-settings-and-the-env-file)
7. [SQLAlchemy sessions and sync vs async](#7-sqlalchemy-sessions-and-sync-vs-async)
8. [Alembic migrations](#8-alembic-migrations)
9. [Password hashing with bcrypt](#9-password-hashing-with-bcrypt)
10. [Sessions and cookie-based login](#10-sessions-and-cookie-based-login)
11. [Protecting routes with dependencies](#11-protecting-routes-with-dependencies)
12. [Auth security details](#12-auth-security-details)
13. [HTMX basics](#13-htmx-basics)
14. [Testing with a rolled-back transaction](#14-testing-with-a-rolled-back-transaction)
15. [Postgres admin: resetting a forgotten password](#15-postgres-admin-resetting-a-forgotten-password)
16. [Foreign keys and relationships](#16-foreign-keys-and-relationships)
17. [Ownership: scoping every query](#17-ownership-scoping-every-query)
18. [Search with ILIKE](#18-search-with-ilike)
19. [Pagination](#19-pagination)
20. [The N+1 query problem](#20-the-n1-query-problem)
21. [Handling HTML forms](#21-handling-html-forms)
22. [Routing details: order, PRG, 404 vs 403](#22-routing-details-order-prg-404-vs-403)
23. [HTMX live search](#23-htmx-live-search)
24. [Jinja2 macros and partials](#24-jinja2-macros-and-partials)
25. [Testing techniques from Phase 2](#25-testing-techniques-from-phase-2)

---

## 1. Choosing the stack: FastAPI vs Django

| | FastAPI | Django |
|---|---|---|
| Philosophy | Small and explicit: you choose and wire the pieces | "Batteries included": admin, auth, ORM, forms built in |
| Getting started | Easier (a few lines per endpoint) | Harder at first (many conventions) |
| Building a full app | More to learn (SQLAlchemy, Alembic, auth) | Faster (it's all built in) |
| Industry | Fastest-growing; default for new APIs, startups, ML/AI | Large installed base; full-stack apps at established companies |

- I chose **FastAPI** because I'm comfortable with Python and SQL, and building auth, the service layer and migrations myself gives me more to explain.
- Jinja2 + HTMX (server-rendered) instead of React means one codebase and one deployment.

> **Interview answer:** "I chose FastAPI over Django because I wanted to design the layers myself: auth, the service layer and migrations, rather than rely on Django's built-ins. FastAPI is also where a lot of new Python backend work is heading. I paired it with SQLAlchemy and Alembic, which are the standard tools for data access and migrations in Python."

---

## 2. Project architecture

A **layered monolith**: one app, one database, three layers.

```
Routers   (app/routers/)    HTTP only: read the request, call a service, render a template
   │
Services  (app/services/)   Business rules: permissions, validation, side effects
   │
Models    (app/models/)     SQLAlchemy tables
   │
PostgreSQL
```

- **Routers never touch the database directly.** They call services.
- **Services know nothing about HTTP**, so they're easy to test.
- **Permission checks live in the service layer**, in one place.
- Supporting folders: `core/` (config, database, security, deps), `schemas/` (Pydantic validation), `templates/` (Jinja2), `tests/`.

> **Interview answer:** "It's a layered monolith. Routers handle HTTP, services hold the business rules, and models handle persistence. Each layer has one job, so I can test business logic without going through HTTP, and permission checks live in one place."

---

## 3. Uvicorn and ASGI

- A browser sends **raw HTTP bytes over TCP**. FastAPI can't open ports or parse HTTP; it's just Python.
- **Uvicorn is the web server.** It listens on a port, parses HTTP, calls the app, and turns the response back into HTTP bytes.
- **ASGI** is the standard interface between server and app. An ASGI app is `async def app(scope, receive, send)`. FastAPI *is* that function (via Starlette).
  - `scope`: dict describing the request (method, path, headers)
  - `receive`: read the request body
  - `send`: send the response
- Because of the standard, you can swap Uvicorn for another ASGI server (Hypercorn, Granian) with no code change.
- **WSGI** (Flask, older Django) is the older, synchronous standard. ASGI adds async and WebSockets.

```powershell
uvicorn app.main:app --reload
#        module   variable  dev-only: restart on file save (uses watchfiles)
```

| | Development | Production |
|---|---|---|
| Host | `127.0.0.1` (only me) | `0.0.0.0` (accept outside connections) |
| `--reload` | On | Off |
| In front | Nothing | The platform's load balancer handles HTTPS |

> **Interview answer:** "FastAPI is an ASGI application. It defines how to handle requests but can't talk to the network itself. Uvicorn is the ASGI server: it listens on a port, parses HTTP, calls the app through the ASGI interface, and sends the response back."

---

## 4. How a request flows through the app

Opening `http://127.0.0.1:8000/`:
1. **Uvicorn** receives the request and calls the FastAPI `app`.
2. **`main.py`** registered the routers with `app.include_router(...)`, so FastAPI knows the URLs.
3. FastAPI matches `@router.get("/")` and runs the **dependencies** first (e.g. `CurrentUser` checks login).
4. The route function runs and returns `templates.TemplateResponse(request, "home.html", {...})`.
5. **Jinja2** renders `home.html`, which `{% extends "base.html" %}` for the shared layout.
6. The HTML goes back through Uvicorn to the browser.

`main.py` only wires things together. Each feature gets its own router file.

---

## 5. PostgreSQL and the database URL

```
postgresql+psycopg://pycrm:pycrm@localhost:5432/pycrm
└── db type ─┘└driver┘└user┘└pass┘└─ host ─┘└port┘└db name┘
```

```
Route code ──► SQLAlchemy (ORM) ──► psycopg (driver) ──► PostgreSQL server
```

**Why Postgres over SQLite or MySQL:**
- **SQLite** is a single file with no server. But it's loose with types, has limited `ALTER TABLE`, and its file gets wiped on free hosting like Render. You'd hit "works locally, breaks in production" bugs.
- **MySQL** is fine, but has no advantage here and fewer free hosting options.
- **Postgres** is the industry default with Python, has free hosting (Neon), and lets me use **the same database locally and in production**.

Only `DATABASE_URL` changes between my laptop and production. The code stays identical.

---

## 6. Settings and the .env file

- `app/core/config.py` defines a `Settings` class (pydantic-settings) that reads **environment variables** and a local `.env` file.
- **Secrets never go in code.** `.env` is git-ignored, and `.env.example` (no real secrets) is committed so others know which variables to set.
- In production, the hosting platform sets the same variables.

> **Interview answer:** "Configuration follows the twelve-factor approach: everything that differs between environments, like the database URL or the secret key, comes from environment variables. Nothing secret is committed."

---

## 7. SQLAlchemy sessions and sync vs async

- A **session** is a unit of work with the database: you load, add and change objects, then `commit()`.
- `get_db()` opens **one session per request** and always closes it afterwards. Routes receive it as `db: DbSession` (dependency injection).
- `pool_pre_ping=True` checks a connection is alive before using it. `connect_timeout=5` makes requests fail fast if the DB is down.
- **Sync, not async:** we use plain synchronous SQLAlchemy. FastAPI runs `def` (non-async) routes in a **thread pool**, so a slow query doesn't block other requests. That's simpler code with good enough concurrency.

> **Interview answer:** "I used synchronous SQLAlchemy because it's simpler to write and test. FastAPI runs sync endpoints in a thread pool, so the server still handles concurrent requests."

---

## 8. Alembic migrations

- A **migration** is a versioned Python file that changes the database schema, with `upgrade()` and `downgrade()`.
- We **never** create or alter tables by hand or with `create_all` in the real app. Every schema change goes through a migration, so every environment ends up identical.

```powershell
alembic revision --autogenerate -m "describe change"   # compare models to DB, write a migration
alembic upgrade head                                    # apply all pending migrations
alembic downgrade -1                                    # undo the last one
alembic check                                           # do models and migrations match?
```

- **Always read an autogenerated migration before applying it.** Autogenerate can miss or misread things.
- `alembic/env.py` imports `app.models` so Alembic sees every table, and reads `DATABASE_URL` from our settings.
- A **naming convention** on `Base.metadata` gives constraints predictable names (e.g. `fk_companies_owner_id_users`).

---

## 9. Password hashing with bcrypt

- **We never store passwords**, only a **hash**: a one-way transformation that can't be reversed.
- **bcrypt** adds a random **salt** to each hash, so two users with the same password get **different hashes**. Attackers can't use precomputed tables.
- bcrypt is **deliberately slow**, which makes brute-forcing leaked hashes expensive.
- bcrypt only uses the first **72 bytes** of a password, so the signup form rejects longer ones.

```python
hash_password("secret")  # "$2b$12$..." (different every time)
verify_password("secret", hashed)  # True
```

> **Interview answer:** "Passwords are hashed with bcrypt, which is slow by design and salted per password, so identical passwords produce different hashes and leaked hashes are expensive to crack."

---

## 10. Sessions and cookie-based login

1. On login, the app checks the password, then stores the user's id in `request.session`.
2. `SessionMiddleware` saves the session in a cookie that is **signed** with `SECRET_KEY`.
3. The browser can **read** the cookie but can't **change** it. If someone edits the user id, the signature no longer matches and the cookie is rejected.
4. On every request, `get_current_user` reads the id from the session and loads the user.

**Why cookies and not JWT?** It's a server-rendered app. The browser sends cookies automatically, and there's no need to store tokens in JavaScript.

> **Interview answer:** "Login stores the user id in a session cookie that's signed with a secret key, so it can't be tampered with. Every protected request reloads the user from the database, which means deactivating someone logs them out immediately."

---

## 11. Protecting routes with dependencies

```python
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/")
def home(request: Request, user: CurrentUser): ...  # must be logged in


@router.get("/users")
def users_page(request: Request, admin: AdminUser): ...  # must be an admin
```

- FastAPI runs the dependency **before** the route. If it raises, the route never runs.
- Not logged in → `LoginRequired` → redirect to `/login?next=<page>`.
- Logged in but not an admin → **403** page.
- Deactivated user → session cleared → redirect to login.
- First user to sign up becomes **admin**; everyone after that is a **sales_rep**.

---

## 12. Auth security details

| Protection | Why |
|---|---|
| Generic "Invalid email or password" | Doesn't reveal which emails have accounts (prevents **user enumeration**) |
| `?next=` only allows paths on our own site | Prevents **open redirects** (`?next=//evil.com`) |
| Cookie `SameSite=lax` | Other sites can't submit forms using my login (basic **CSRF** protection) |
| Logout is a POST, not a link | Another site can't log me out with an `<img>` tag |
| `session.clear()` before login | No data from an old session carries over |
| Admin can't demote or deactivate self | Prevents locking everyone out |
| Emails stored lowercase | `Ada@X.com` and `ada@x.com` are the same account |

---

## 13. HTMX basics

HTMX lets HTML elements make requests and swap in the response, with **no page reload and no custom JavaScript**.

```html
<button hx-get="/health" hx-target="#health" hx-swap="innerHTML">Check</button>
<pre id="health"></pre>
```

- `hx-get` / `hx-post`: which URL to call
- `hx-target`: which element to update
- `hx-swap`: how (`innerHTML` replaces the contents; `outerHTML` replaces the element itself)
- `hx-vals`: extra values to send

**The pattern:** the server returns a **partial template** (e.g. one table row), and HTMX swaps it in. On the users page, changing a role re-renders only that user's row.

**Redirects:** a normal redirect would be swapped *into* the page, so for HTMX requests we send an `HX-Redirect` header and HTMX does a full-page redirect.

---

## 14. Testing with a rolled-back transaction

- Tests run against a separate **`pycrm_test`** database, never the dev data.
- Each test runs inside a **transaction that's rolled back** at the end, so every test starts with empty tables and tests can't affect each other.
- `join_transaction_mode="create_savepoint"`: the app's own `db.commit()` only commits a savepoint inside that outer transaction.
- `app.dependency_overrides[get_db] = ...` swaps the real DB session for the test one. The same trick lets a `FakeSession` simulate the database being down.
- `TestClient` acts as a browser and keeps cookies between requests, so login works in tests.

> **Interview answer:** "Tests run against a real Postgres test database, not SQLite, so they match production. Each test is wrapped in a transaction that's rolled back, which makes them fast and isolated. I use FastAPI's dependency overrides to inject the test session."

---

## 15. Postgres admin: resetting a forgotten password

- **`pg_hba.conf`** ("host-based authentication") controls who must give a password.
- To reset: temporarily set the local lines to `trust` → restart the service → `ALTER USER postgres WITH PASSWORD '...'` → restore `scram-sha-256` → restart.
- **Never leave `trust` on**: anyone on the machine could log in as any user.
- In psql, SQL statements only run when they end with `;`. The prompt `postgres-#` means "statement not finished yet", and `\r` clears it.

---

## 16. Foreign keys and relationships

**Foreign key** (database side): a column that must hold the `id` of an existing row in another table. Postgres **enforces** it.

```python
owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
```

**`ondelete`** says what happens when the referenced row is deleted:

| Option | Effect | Use for |
|---|---|---|
| default / `RESTRICT` | Refuse the delete | Owners. We deactivate users, never delete them. |
| `CASCADE` | Delete the children too | Rarely; it's easy to lose data |
| `SET NULL` | Keep the children, clear the link | Contact → Company |

**Index foreign keys.** Postgres doesn't do it automatically, and queries like "my companies" (`WHERE owner_id = ?`) need the index.

**Relationship** (Python side): navigate objects instead of ids.

```python
owner: Mapped["User"] = relationship(back_populates="companies")  # on Company
companies: Mapped[list["Company"]] = relationship(back_populates="owner")  # on User

company.owner  # <User 1 S>
user.companies  # [<Company 10 Acme>, ...]
```

- `back_populates` links both directions and keeps them in sync.
- **Nullability comes from the type hint:** `Mapped[str]` gives NOT NULL, `Mapped[str | None]` allows NULL.
- Use `String(n)` for short fields and `Text` for long free-form notes.
- `if TYPE_CHECKING:` imports avoid **circular imports** between models that refer to each other.
- The `ForeignKey` takes `"table.column"`; the relationship takes the **class name** in quotes.

> **Interview answer:** "Foreign keys enforce integrity at the database level, so you can't have a company owned by a user who doesn't exist. I index them because most queries filter by owner. On the Python side, SQLAlchemy relationships let me write `company.owner` instead of manual joins."

---

## 17. Ownership: scoping every query

**Rule:** sales reps see only the records they own; admins see everything.

```python
def visible_to(stmt, model, user):
    if user.is_admin:
        return stmt
    return stmt.where(model.owner_id == user.id)

# every list and lookup goes through it
stmt = visible_to(select(Company), Company, user).where(Company.id == company_id)
```

- The rule lives in **one function** (`app/services/common.py`), used by every list, detail, edit and delete. If each route filtered by hand, forgetting it once would leak data.
- Fetching a single record also goes through the scope: someone else's company returns `None`, so the route returns **404**.
- **Linking rule:** a rep can only attach a contact to a company they can see, checked in `contact_service._check_company`. Keeping a contact's existing company is always allowed.

> **Interview answer:** "Authorization is enforced in the service layer by one helper that adds `WHERE owner_id = current_user` unless the user is an admin. Every query goes through it, so there's one place to get right and one place to test, and tests check that a rep gets 404 on another rep's records."

---

## 18. Search with ILIKE

```python
pattern = f"%{escape_like(search)}%"
stmt.where(or_(Company.name.ilike(pattern, escape="\\"), Company.industry.ilike(pattern, escape="\\")))
```

- `ILIKE` is Postgres's **case-insensitive** `LIKE`. `%` means "any characters".
- **Escape the user's input:** `%` and `_` are wildcards, so searching `"%"` would match everything. `escape_like()` makes them literal.
- Searching contacts by **company name** needs a join: `stmt.outerjoin(Contact.company)`. It's an *outer* join so contacts with no company still appear.
- SQLAlchemy uses **bound parameters**, so user input is never pasted into SQL. That's why this is safe from **SQL injection**.
- At much larger scale you'd use Postgres **full-text search** or a trigram index. `ILIKE '%x%'` can't use a normal index.

---

## 19. Pagination

```python
total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
items = db.scalars(stmt.limit(20).offset((page - 1) * 20))
```

- **LIMIT/OFFSET**: page 3 at 20 per page means `LIMIT 20 OFFSET 40`.
- A second **COUNT** query gives the total, for "Showing 21–40 of 95" and the number of pages.
- **Always `ORDER BY` something unique** (we add `id` as a tie-breaker). Otherwise rows can appear on two pages or on none.
- Out-of-range page numbers are **clamped** to the valid range.
- Pagination links **keep the current filters** (`?q=acme&page=2`).
- Trade-off: OFFSET gets slow on very deep pages. The alternative is **keyset (cursor) pagination** (`WHERE id > last_seen_id`). OFFSET is fine at CRM scale.

---

## 20. The N+1 query problem

The contacts list shows each contact's company. With lazy loading:

```
1 query:     SELECT * FROM contacts LIMIT 20
+20 queries: SELECT * FROM companies WHERE id = ?   ← one per row!
```

That's **N+1 queries**. The page gets slower with every row and it's invisible in the code.

**Fix: eager loading.**

```python
select(Contact).options(selectinload(Contact.company), selectinload(Contact.owner))
# 1 query for contacts + 1 for all their companies (WHERE id IN (...)) + 1 for owners
```

| Strategy | How | Good for |
|---|---|---|
| `selectinload` | Second query with `WHERE id IN (...)` | Most cases, and collections |
| `joinedload` | A `JOIN` in the same query | Single related objects (many-to-one) |

**Proven by a test:** `test_list_query_count_does_not_grow_with_rows` counts SQL statements for 3 rows and for 15 rows and asserts they're equal. With `selectinload` removed, it fails: **7 queries vs 19**.

> **Interview answer:** "I hit the N+1 problem on list pages that show related data, like each contact's company. I fixed it with `selectinload`, which loads all the related rows in one extra query. I also wrote a test that counts the SQL statements, so a regression would be caught."

---

## 21. Handling HTML forms

- **HTML sends every field as a string**, and an empty input arrives as `""`. A shared `FormModel` base class strips whitespace and turns `""` into `None`, so optional fields become `NULL` and required fields fail with "This field is required".
- **One schema per form** (`CompanyForm`, `ContactForm`), validated with `CompanyForm.model_validate(form_data)`.
- **Reading the whole form:** an **async dependency** (`FormData`) awaits `request.form()`, while the routes stay plain `def` and run in the thread pool with our sync DB code. (An `async def` route doing sync DB calls would block the event loop.)
- **On error,** re-render the form with status **400**, the error message, and **what the user typed**, so nothing is lost.
- **Normalising input:** `acme.com` is stored as `https://acme.com`. This also blocks `javascript:` links, a classic **XSS** trick when you render user input as `href`.

---

## 22. Routing details: order, PRG, 404 vs 403

**Route order matters.** `/companies/new` must be declared **before** `/companies/{company_id}`, or FastAPI tries to parse `"new"` as an integer id.

**Post/Redirect/Get (PRG):** after a successful POST, respond with `303 See Other` to the detail page. Refreshing the page then reloads the GET instead of re-submitting the form (no duplicate records).

**404 vs 403 for other people's records:**

| Situation | Response | Why |
|---|---|---|
| Rep opens `/users` (admin page) | **403 Forbidden** | The page exists; they just lack the role |
| Rep opens another rep's `/companies/42` | **404 Not Found** | Don't reveal that record 42 exists |

**Delete is a POST** with a browser `confirm()`, never a GET link, so crawlers or prefetching can't delete data.

---

## 23. HTMX live search

```html
<form hx-get="/companies" hx-target="#results" hx-push-url="true"
      hx-trigger="input delay:300ms, submit">
  <input type="search" name="q"> <select name="industry">…</select>
</form>
<div id="results">{% include "partials/company_results.html" %}</div>
```

- `hx-trigger="input delay:300ms"` waits until typing pauses for 300ms (**debouncing**), so there's one request, not one per keystroke.
- The whole form is sent, so search and filter work together.
- The server checks the `HX-Target: results` header and returns **only the table partial**; a normal request gets the full page.
- `hx-push-url="true"` updates the address bar, so the back button and shared links work.
- **Progressive enhancement:** the form also has a normal `method="get"`, so it still works without JavaScript.

---

## 24. Jinja2 macros and partials

**Macros** are reusable template functions:

```jinja
{% macro field(name, label, values, type="text", required=false) %} ... {% endmacro %}

{% from "macros/forms.html" import field %}
{{ field("name", "Name", values, required=true) }}
```

**Partials** are template fragments used in two ways: included in the full page, and returned alone for HTMX (`partials/company_results.html`, `partials/pagination.html`, `partials/user_row.html`).

**Autoescaping:** Jinja escapes `<`, `>`, `&` and quotes in `{{ }}` output, so user data can't inject HTML (XSS). For JavaScript strings, use `|tojson`, as in the delete confirmation.

---

## 25. Testing techniques from Phase 2

- **Factory fixtures** (`make_company`, `make_contact`) create test data in one line. **Role fixtures** (`admin`, `rep`, `other_rep`) make tests read like the scenario.
- **`@pytest.mark.parametrize`** runs one test for many inputs. One test covers GET detail, GET edit, POST edit and POST delete all returning 404.
- **Counting queries:** a SQLAlchemy event listener (`before_cursor_execute`) records every statement, which is how the N+1 test works.
- **Prove a test can fail:** temporarily break the code (remove `selectinload`) and check that the test goes red. A test that can never fail proves nothing.
- `db.expire_all()` makes the session forget cached objects, imitating a fresh request.
- `db.refresh(obj)` reloads a row after the database changed it (e.g. `ON DELETE SET NULL`).
