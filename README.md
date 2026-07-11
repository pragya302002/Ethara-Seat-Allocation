# Ethara AI — Enterprise Seat Allocation & Project Mapping System

Technical assessment submission. Full-stack system for managing employee
seating, project assignments, and occupancy analytics for a ~5,000-employee
organization.

**Stack:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL · Next.js + React
Query + Tailwind · JWT auth · Claude-powered natural language query
assistant.

---

## Live deployment

| | |
|---|---|
| Frontend | *fill in after Vercel deploy* |
| Backend API | *fill in after Railway deploy* |
| API Docs (Swagger) | `<backend-url>/docs` |
| Demo login | any seeded employee email · password `Password123!` |
| Demo admin | see seed output, or query `role=admin` |

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for exact deploy steps.

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
- AI Assistant: natural-language read-only queries via Claude tool-use
  (structurally verified; live round-trip needs `ANTHROPIC_API_KEY` set,
  which wasn't available in the dev sandbox — see Debugging Notes)
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

## Architecture

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
