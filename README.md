# Ethara AI — Enterprise Seat Allocation & Project Mapping System

Technical assessment submission. Full-stack system for managing employee
seating, project assignments, and occupancy analytics for a ~5,000-employee
organization.

**Stack:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL · Next.js + React
Query + Tailwind · JWT auth · Groq-powered natural language query
assistant.

---

## Live deployment

| | |
|---|---|
| Frontend | [ethara-seat-allocation-phi.vercel.app](https://ethara-seat-allocation-phi.vercel.app) |
| Backend API | [ethara-seat-allocation-production.up.railway.app](https://ethara-seat-allocation-production.up.railway.app) |
| API Docs (Swagger) | [ethara-seat-allocation-production.up.railway.app/docs](https://ethara-seat-allocation-production.up.railway.app/docs) |
| Health check | [ethara-seat-allocation-production.up.railway.app/health](https://ethara-seat-allocation-production.up.railway.app/health) |
| Demo login | any seeded employee email (see `docs/sample_data/employees_sample.csv`) · password `Password123!` |
| Demo admin | `eric.bernard1@etharatest.com` · password `Password123!` |

All of the above have been live-tested end-to-end (login, employee
search, seat allocate/release, dashboard, and the AI Assistant) against
the real deployed instances — not just built and assumed to work. See
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the exact deploy steps,
and [`docs/DEBUGGING.md`](docs/DEBUGGING.md) for the real issues hit and
fixed during deployment (Windows-specific Python driver issues, Railway
configuration gotchas, and the Anthropic→Groq switch).

---

## Scope note (read this first)

This was built end-to-end within a tightened submission window (48 hours,
not the originally-planned multi-week enterprise timeline the brief's
scale would normally warrant for every listed feature at full depth). To
keep what ships **working and tested** rather than broad-and-fragile, the
following scope decisions were made explicitly rather than silently:

**Built and tested end-to-end:**
- Full auth (JWT, bcrypt, 4-role RBAC: Admin/HR/PM/Employee)
- Employee CRUD + structured search/filter/pagination
- Seat allocation: allocate / release / transfer / history, with
  database-level concurrency safety (see `seat_service.py`)
- Project CRUD + assignment/removal, with the same concurrency pattern
- Dashboard: occupancy, department/project/floor breakdowns, recent
  activity — all against real seeded data
- AI Assistant: natural-language read-only queries via tool-calling.
  Originally built against the Anthropic API; switched to Groq's
  free-tier API after the Anthropic test account hit a billing gate — a
  real code change (different tool-calling schema), not just a config
  swap. See `docs/DEBUGGING.md` entries 9–10. **Live-confirmed working
  against the deployed Railway backend** with real seeded data (e.g.
  "List employees working for Acme Corp" correctly returns real matches).
- Full deployment: GitHub → Railway (backend + Postgres) → Vercel
  (frontend), with CORS correctly scoped between them. Every layer
  live-tested from the actual deployed URLs, not just locally.
- 5,000-employee realistic seed data (departments, projects, office
  hierarchy, seat/project assignment history)
- 9 backend tests covering auth, RBAC, and the seat-allocation
  concurrency logic — all passing against real Postgres

**Scoped down, documented, not silently dropped:**
- **CSV bulk upload** — not implemented. The CRUD and validation patterns
  it would reuse are already in place (`EmployeeCreate` schema,
  `EmployeeRepository`); given more time this is a ~2-hour addition using
  `python-multipart` (already a dependency) + per-row validation with a
  partial-success error report.
- **PM-scoped project views** — Project Managers currently get the same
  read access as HR/Admin rather than a project-scoped filtered view.
  Confirmed acceptable scope with the requester (see `AI_PROMPTS.md`).
- **Frontend**: 5 core screens (login, dashboard, employees, seats, AI
  assistant) rather than all ~9 implied by the brief. Project management
  and detailed seat-map/floor-plan visualization screens are not built —
  the underlying APIs exist and are tested, so this is a frontend-only gap.
- **Heat map visualization** — floor utilization data is served by the
  API and shown as a bar/pie chart; a literal heat-map visual wasn't built.
- **Test coverage** — 9 tests target the highest-risk logic (auth, RBAC,
  concurrency-safe seat allocation) rather than exhaustive coverage of
  every endpoint.

---

## Spec-compliance addendum

The above scope note describes the system as originally built. Partway
through the submission window, the actual attached assessment document
(with exact functional requirements, business rules, and API specs) was
found to have been overlooked in favor of an earlier self-written draft.
The following changes were made to align with the real spec, all
live-tested against the real deployed system — see `AI_PROMPTS.md` entry
22 and `docs/DEBUGGING.md` for full detail:

- **Seat status** renamed to the spec's exact values:
  `Available / Occupied / Reserved / Maintenance`
- **`bay`** added as a real field on every seat (Floor → Zone → Bay →
  Seat Number, matching the spec's hierarchy)
- **Seed data** replaced with the spec's exact 11 project names (Indigo,
  Indreed, Mydreed, Preed, Serfy, Oreed, Bedegreed, Opreed, Serry, Kaary,
  Mered) and resized to meet every stated minimum: 5,520 seats (≥5,500),
  180 reserved (≥100), 502 employees pending allocation (≥50), 48 zones
  (≥10), 6 floors (≥5)
- **New endpoints**: `GET/POST /seats`, `GET /seats/available`,
  `GET /seats/suggest` (proximity-based new-joiner allocation — suggests
  seats in the zone where most of an employee's project teammates
  already sit, falling back to any available seat if none are nearby),
  `GET /projects/{id}/employees`, `GET /dashboard/project-utilization`,
  `GET /dashboard/floor-utilization`, `POST /ai/query` (spec's exact
  `{"query": ...} → {"answer": ...}` contract), and a `PUT` alias
  alongside the existing `PATCH` for employee updates
- **Employee records** now surface `current_project_name` and
  `seat_allocation_status` directly, computed via query-time joins
- **Deliberately not done**: a full schema rewrite to match the spec's
  simpler suggested table structure (no history tables). The existing
  `SeatAllocation`/`ProjectAssignment` history-table design was judged
  too valuable — and too risky to unwind on a live, already-debugged
  production system with limited time remaining — so the spec's required
  *fields* are exposed via joins on top of the existing correct
  architecture, rather than migrating to a different schema shape.

---

```
backend/
  app/
    api/v1/          # FastAPI routers — HTTP layer only, no business logic
    services/        # Business logic, transactions, authorization decisions
    repositories/     # All raw SQLAlchemy queries — services never import `select` directly
    models/           # SQLAlchemy ORM models
    schemas/           # Pydantic request/response contracts
    core/              # config, security (JWT/bcrypt), auth dependencies
    database/          # async engine/session setup
    seed/               # realistic data generator
  alembic/               # migrations
  tests/                  # pytest suite (async, real Postgres)

frontend/
  src/
    app/                 # Next.js App Router pages
    components/           # Reusable UI (AppShell, StatCard, ...)
    hooks/                  # useAuth, QueryProvider
    services/                # typed API client functions
    types/                    # TypeScript types mirroring backend Pydantic schemas
    lib/                       # axios instance with JWT interceptor
```

**Why repository pattern + service layer:** every business rule (seat
occupancy transitions, "an employee has at most one active seat",
RBAC-gated writes) lives in `services/`, and every SQL query lives in
`repositories/`. Routers stay thin — they just wire HTTP to services. This
is what let the seat-allocation concurrency logic get unit-tested without
spinning up the full HTTP stack for every case, and it's the boundary a
CSV-upload feature or a PM-scoped-view feature would plug into without
touching existing code.

**Why history tables instead of a `current_seat_id` FK on Employee:**
`SeatAllocation` and `ProjectAssignment` rows have a nullable
`release_date`/`end_date` — NULL means "currently active." This is what
makes "View History," the dashboard's "Recent Allocations/Releases," and
"employees without a seat" all simple queries instead of requiring a
separate audit-log system bolted on afterward. Full reasoning is in the
docstrings of `models/seat.py` and `models/project.py`.

**Why Postgres partial unique indexes for concurrency:** rather than a
hand-rolled "check then write" race in application code, the database
itself enforces "at most one active allocation per seat" and "at most one
active allocation per employee." The service layer catches the resulting
`IntegrityError` and returns a clean `409`. This was tested directly (see
`tests/test_seats.py::test_allocate_already_occupied_seat_returns_409`) —
a real conflict is provably rejected, not just assumed to be.

---

## Local setup

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET_KEY
alembic upgrade head
python3 -m app.seed.seed     # takes ~5-10s for 5,000 employees
uvicorn app.main:app --reload
```
API docs at `http://localhost:8000/docs`.

> **Windows note:** `asyncpg` (the default async Postgres driver) requires
> a C++ compiler to build on Windows with newer Python versions, since it
> doesn't ship pre-built wheels there. If `pip install` fails with a
> Visual C++ Build Tools error, switch to `psycopg[binary,pool]` instead
> (has native Windows wheels) — swap the dependency in
> `requirements.txt` and change `postgresql+asyncpg://` to
> `postgresql+psycopg://` in `app/core/config.py`. Windows also requires
> the Selector event loop policy for async Postgres drivers — see the
> `sys.platform == "win32"` check at the top of `app/database/session.py`
> and `alembic/env.py`. Full details of both issues in
> `docs/DEBUGGING.md`.

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_URL at your backend
npm run dev
```

### Tests
```bash
cd backend
pytest tests/ -v
```

---

## Documentation

- [`AI_PROMPTS.md`](AI_PROMPTS.md) — every AI-assisted development step, per the assessment's traceability requirement
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Railway + Vercel deployment steps
- [`docs/DEBUGGING.md`](docs/DEBUGGING.md) — real bugs caught and fixed during this build, with root causes
- [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) — table-by-table schema reference
