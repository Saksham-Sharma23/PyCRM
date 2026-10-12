# PyCRM

A simple CRM for managing companies, contacts, deals and tasks.

**Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · Jinja2 + HTMX · Tailwind CSS · pytest

## Running locally

Requirements: Python 3.12+, and either Docker Desktop or a local PostgreSQL install.

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt

# 2. Configure environment
copy .env.example .env          # macOS/Linux: cp .env.example .env

# 3. Start PostgreSQL (skip if you installed Postgres locally)
docker compose up -d

# 4. Apply database migrations
alembic upgrade head

# 5. Run the app
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and sign up. **The first account created becomes the admin**; later signups are sales reps, and the admin can change roles on the Users page.

## Development

Tests use a separate database, `pycrm_test` (override with the `TEST_DATABASE_URL` environment variable). Create it once:

```sql
CREATE DATABASE pycrm_test OWNER pycrm;
```

```bash
pytest            # run tests
ruff check .      # lint
ruff format .     # format
```
