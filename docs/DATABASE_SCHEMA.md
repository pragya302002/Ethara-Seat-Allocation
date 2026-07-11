# Database Schema Reference

8 tables, PostgreSQL. Full source of truth is
`backend/app/models/*.py` — this document is a human-readable summary
generated from the actual applied schema (verified via `\d+` against a
real Postgres instance, not written from the ORM code alone).

## Entity relationship overview

```
Department ──< Employee >── Employee (self-ref: manager_id)
                  │
                  ├──< ProjectAssignment >── Project ──> Employee (manager_id)
                  │
                  └──< SeatAllocation >── Seat ──> Zone ──> Floor ──> Building
```

## Tables

### `departments`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| name | varchar(120) | unique, indexed |
| code | varchar(20) | unique |

### `buildings` / `floors` / `zones`
Physical office hierarchy. `floors.floor_number` is unique per building;
`zones.name` is unique per floor. Row is *not* a separate table — it's a
plain string column on `Seat` (see `models/location.py` docstring for
why: a Row has no independent attributes or query pattern that would
justify the extra join).

### `employees`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| employee_code | varchar(20) | unique, indexed |
| full_name | varchar(150) | indexed |
| email | varchar(180) | unique, indexed — also the auth identity |
| hashed_password | varchar(255) | bcrypt |
| role | enum | admin / hr / project_manager / employee |
| department_id | uuid FK → departments | ON DELETE SET NULL |
| designation | varchar(120) | |
| manager_id | uuid FK → employees (self) | ON DELETE SET NULL — reporting manager |
| employment_status | enum | active / on_leave / notice_period / terminated |
| date_of_joining | date | |
| location | varchar(120) | office city label |
| is_active | boolean | soft-delete flag |

**Design note:** Employee doubles as the auth identity (no separate
`users` table). See `models/employee.py` docstring for the reasoning and
the condition under which this should be split later.

### `projects`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| name | varchar(150) | indexed |
| code | varchar(30) | unique |
| client | varchar(150) | indexed |
| manager_id | uuid FK → employees | ON DELETE SET NULL |
| team_size_target | int | |
| start_date / end_date | date | end_date NULL = ongoing |
| is_active | boolean | |

### `project_assignments` (history table)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| employee_id | uuid FK → employees | ON DELETE CASCADE |
| project_id | uuid FK → projects | ON DELETE CASCADE |
| start_date | date | |
| end_date | date, nullable | **NULL = currently active assignment** |

**Constraint:** partial unique index on `employee_id` WHERE
`end_date IS NULL` — enforces "at most one active project per employee"
at the database level, not just in application code.

### `seats`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| seat_number | varchar(20) | unique per zone |
| zone_id | uuid FK → zones | ON DELETE CASCADE |
| row_label | varchar(10), nullable | |
| seat_type | enum | standard / standing_desk / cabin / meeting_pod / accessible |
| status | enum | vacant / occupied / reserved / out_of_service — **denormalized cache**, see below |

### `seat_allocations` (history table)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| seat_id | uuid FK → seats | ON DELETE CASCADE |
| employee_id | uuid FK → employees | ON DELETE CASCADE |
| event_type | enum | allocate / release / transfer / reserve |
| allocation_date | date | |
| release_date | date, nullable | **NULL = currently occupying this seat** |

**Constraints:** two partial unique indexes, both `WHERE release_date IS
NULL`:
- on `seat_id` — at most one active allocation per seat
- on `employee_id` — at most one active seat per employee

## Why history tables instead of a direct FK

An employee's "current seat" or "current project" is *derived* — query
for the row with a NULL end date — rather than stored as a direct
`current_seat_id` column on `Employee`. This single design choice is what
makes several brief requirements simple queries instead of a bolted-on
audit log:
- "View History" → all rows for a seat/employee, ordered by date
- Dashboard "Recent Allocations / Recent Releases" → filter + order the
  same table
- "Employees without a seat" → `NOT IN (SELECT employee_id FROM
  seat_allocations WHERE release_date IS NULL)`
- Transfer → release + allocate as one atomic transaction, both rows
  independently auditable afterward

## Why `seats.status` is denormalized

`status` on `Seat` is a cached copy of "does this seat have an active
`SeatAllocation`," kept in sync by the service layer on every
allocate/release/transfer. This trades a small consistency-management
cost (the service must remember to update it) for a plain indexed
`WHERE status = 'vacant'` on the dashboard's most frequently-hit query,
instead of a correlated subquery against `seat_allocations` on every
occupancy check. Verified in testing that `occupied` count always exactly
equals active `seat_allocations` count (see `AI_PROMPTS.md` entry on
seed data validation).

## Concurrency safety

Every "only one active X" business rule (one seat per employee, one
occupant per seat, one active project per employee) is enforced by a
**Postgres partial unique index**, not application-level check-then-write
logic. The service layer catches the resulting `IntegrityError` on a
race and returns a clean `409 Conflict`. This is tested directly — see
`backend/tests/test_seats.py`.
