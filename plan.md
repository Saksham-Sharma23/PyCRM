# PyCRM — Development Plan

A simple CRM for a single team: companies, contacts, deals (with a Kanban pipeline), activities, tasks and a dashboard.

**Stack:** FastAPI · SQLAlchemy 2.0 (sync) · Alembic · PostgreSQL · Jinja2 + HTMX · Tailwind CSS · pytest · ruff · GitHub Actions · Render + Neon

**Architecture:** layered monolith. Routers (HTTP) → Services (business rules) → Models (database).

Each phase ends with a working app and a git commit.

---

## Phase 0 — Setup
- [x] Virtual environment
- [ ] Git repo (`git init`)
- [x] Folder structure (`core/`, `models/`, `schemas/`, `services/`, `routers/`, `templates/`, `static/`)
- [x] Settings from `.env` (`config.py`)
- [x] Database engine and per-request session (`database.py`)
- [x] Alembic configured to use app settings and models
- [x] `base.html` layout with Tailwind + HTMX, home page, `/health` endpoint
- [x] ruff and pytest configured, first tests passing
- [x] `docker-compose.yml` for local Postgres
- [x] Choose how to run Postgres: PostgreSQL 18 Windows installer
- [x] `/health` shows `"database": "ok"` (verified against a real Postgres)
- [ ] First commit
- [ ] Push to GitHub

**Done when:** the app runs locally against Postgres, tests pass, and the code is on GitHub.

## Phase 1 — Auth & Users
- [x] `User` model (name, email, password_hash, role, is_active) and first Alembic migration
- [x] Password hashing with bcrypt
- [x] Signup, login and logout pages
- [x] Session cookie auth (`SessionMiddleware`)
- [x] `get_current_user` and `require_admin` dependencies
- [x] Roles: `admin` and `sales_rep` (first user to sign up becomes admin)
- [x] Admin page to manage users (change role, activate/deactivate, via HTMX)
- [x] Test database setup and auth tests (28 tests passing)
- [x] End-to-end check: real server + real Postgres, 25 HTTP checks (signup, logout, login, roles, deactivate, 403/404 pages)
- [ ] Commit
- [ ] Your machine: start the `postgresql-x64-18` service (admin), create the `pycrm` user + `pycrm` and `pycrm_test` databases, run `alembic upgrade head`
- [ ] Click through it yourself in a browser

**Done when:** protected pages redirect to login, and auth tests pass.

## Phase 2 — Companies & Contacts
- [ ] `Company` and `Contact` models and migration
- [ ] Create, view, edit, delete for both
- [ ] List pages with search, filters and pagination
- [ ] Detail pages (a company shows its contacts)
- [ ] Ownership rules: reps see their own records, admins see all
- [ ] Tests

**Done when:** a rep can manage only their own records, and an admin sees everything.

## Phase 3 — Deals & Pipeline
- [ ] `Deal` model (stages: lead → qualified → proposal → negotiation → won / lost) and migration
- [ ] Deal create, view, edit, delete
- [ ] Kanban board with drag-and-drop between stages (SortableJS + HTMX)
- [ ] Stage change is logged automatically as an activity
- [ ] Tests

**Done when:** dragging a card updates the database and logs an activity.

## Phase 4 — Activities & Tasks
- [ ] `Activity` and `Task` models and migration
- [ ] Timeline on contact and deal pages (add note / call / email / meeting)
- [ ] Tasks with due dates, linked to a contact or deal
- [ ] "My tasks" page with an overdue view
- [ ] Tests

**Done when:** tasks and timelines work from every detail page.

## Phase 5 — Dashboard
- [ ] Pipeline value by stage
- [ ] Win rate
- [ ] Deals closing this month
- [ ] Overdue tasks
- [ ] Charts (Chart.js)
- [ ] Dashboard is the landing page after login

**Done when:** the dashboard gives a useful overview at a glance.

## Phase 6 — Quality
- [ ] Fill test gaps
- [ ] GitHub Actions CI (ruff + pytest on every push)
- [ ] Seed script with a demo account and realistic sample data

**Done when:** CI is green and one command seeds a demo.

## Phase 7 — Deploy & README
- [ ] Production `Dockerfile`
- [ ] Neon Postgres database
- [ ] Render web service, with migrations running on deploy
- [ ] README with screenshots/GIF, architecture diagram, live link and demo login

**Done when:** there's a public URL that recruiters can log into.

## Phase 8 — Stretch (pick 1–2)
- [ ] CSV import/export of contacts
- [ ] JSON REST API under `/api`
- [ ] Daily email digest of due tasks
- [ ] AI summary of a contact's history

---

## Decisions log
| Date | Decision | Why |
|---|---|---|
| 2026-10-12 | FastAPI over Django | More of the system is my own design, so there's more to explain in interviews; matches where hiring is heading |
| 2026-10-12 | PostgreSQL | Same database locally and in production; free hosting (Neon); industry standard |
| 2026-10-12 | Jinja2 + HTMX instead of React | One codebase and one deployment; simpler to build and explain |
| 2026-10-12 | Single-org, not multi-tenant | Keeps the data model and permissions simple |
| 2026-10-12 | Sync SQLAlchemy | Simpler to write and test; FastAPI runs sync routes in a thread pool |
| 2026-10-12 | Signed session cookie instead of JWT | Server-rendered app, so cookies are the natural fit; nothing to store client-side in JS |
| 2026-10-12 | First user to sign up becomes admin | No separate admin-creation script needed; easy to explain |
| 2026-10-12 | Roles stored as VARCHAR, not a native Postgres enum | Adding a role later needs no enum migration |
| 2026-10-12 | Tests run in a rolled-back transaction on a `pycrm_test` DB | Fast, isolated tests against the real database engine |
