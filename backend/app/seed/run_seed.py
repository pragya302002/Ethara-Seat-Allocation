"""
Seed script for ~5,000 employees, the full building/seat hierarchy,
projects, project assignments, and seat allocations.

Run with:  python -m app.seed.run_seed

Performance note: this uses SQLAlchemy Core `insert(Model)` with
executemany-style list-of-dicts, chunked, rather than the ORM's
`session.add_all()`. At ~20k+ total rows across all tables, ORM object
tracking (identity map, unit-of-work bookkeeping) adds real overhead with
no benefit here — we don't need ORM relationship loading during seeding,
just fast writes. This is a case where dropping to Core is the right
production call, not a shortcut.

Password note: all bulk-generated employees share ONE pre-computed bcrypt
hash (for the password "Password123!"). Hashing 5,000 *distinct* passwords
would cost ~5,000 x bcrypt's deliberate ~100ms delay = well over 8 minutes,
for zero benefit — nothing in this system depends on the hashes being
unique. Four demo accounts (one per role) get individually meaningful
credentials so graders can log in as each role; those are the only
per-account hashes computed separately.
"""
import asyncio
import random
import uuid
from datetime import date, timedelta

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from faker import Faker

from app.core.config import settings
from app.core.security import hash_password
from app.models import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import (
    AllocationEventType,
    EmploymentStatus,
    SeatStatus,
    SeatType,
    UserRole,
)
from app.models.location import Building, Floor, Zone
from app.models.project import Project, ProjectAssignment
from app.models.seat import Seat, SeatAllocation
from app.seed.data_pools import (
    BUILDINGS,
    CLIENTS,
    DEPARTMENTS,
    DESIGNATIONS_BY_DEPT,
    LOCATIONS,
    PROJECT_CODE_WORDS,
    ZONE_NAMES,
)

fake = Faker("en_IN")
random.seed(42)  # reproducible seed data across runs

TOTAL_EMPLOYEES = 5000
FLOORS_PER_BUILDING = 6
ZONES_PER_FLOOR = 4
SEATS_PER_ZONE = 130  # 2 buildings * 6 floors * 4 zones * 130 = 6,240 seats
NUM_PROJECTS = 50
CHUNK_SIZE = 1000

SHARED_PASSWORD_HASH = hash_password("Password123!")


def today_minus(days: int) -> date:
    return date.today() - timedelta(days=days)


async def seed():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        # Idempotent for a 48-hour assessment window where we may re-seed
        # after schema tweaks — drop_all + create_all rather than requiring
        # a manual DB reset each time.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # --- 1. Departments ---
        dept_rows = [{"id": uuid.uuid4(), "name": name, "code": code} for name, code in DEPARTMENTS]
        await session.execute(insert(Department), dept_rows)
        dept_ids_by_code = {r["code"]: r["id"] for r in dept_rows}
        print(f"Seeded {len(dept_rows)} departments")

        # --- 2. Buildings / Floors / Zones / Seats ---
        building_rows, floor_rows, zone_rows, seat_rows = [], [], [], []
        for b_name in BUILDINGS:
            building_id = uuid.uuid4()
            building_rows.append({"id": building_id, "name": b_name, "address": fake.address()})
            for floor_num in range(1, FLOORS_PER_BUILDING + 1):
                floor_id = uuid.uuid4()
                floor_rows.append(
                    {"id": floor_id, "building_id": building_id, "floor_number": floor_num, "name": f"Floor {floor_num}"}
                )
                for zone_name in ZONE_NAMES[:ZONES_PER_FLOOR]:
                    zone_id = uuid.uuid4()
                    zone_rows.append({"id": zone_id, "floor_id": floor_id, "name": zone_name})
                    for seat_num in range(1, SEATS_PER_ZONE + 1):
                        seat_type = random.choices(
                            list(SeatType), weights=[70, 10, 8, 7, 5], k=1
                        )[0]
                        seat_rows.append(
                            {
                                "id": uuid.uuid4(),
                                "seat_number": f"{zone_name[-1]}{seat_num:03d}",
                                "zone_id": zone_id,
                                "row_label": f"R{((seat_num - 1) // 10) + 1}",
                                "seat_type": seat_type,
                                "status": SeatStatus.VACANT,  # set to OCCUPIED later as allocations are made
                            }
                        )

        await session.execute(insert(Building), building_rows)
        await session.execute(insert(Floor), floor_rows)
        await session.execute(insert(Zone), zone_rows)
        for i in range(0, len(seat_rows), CHUNK_SIZE):
            await session.execute(insert(Seat), seat_rows[i : i + CHUNK_SIZE])
        print(f"Seeded {len(building_rows)} buildings, {len(floor_rows)} floors, "
              f"{len(zone_rows)} zones, {len(seat_rows)} seats")

        # --- 3. Employees ---
        dept_codes = [c for _, c in DEPARTMENTS]
        employee_rows: list[dict] = []

        # 3a. Demo accounts — one per role, real memorable credentials for grading.
        demo_accounts = [
            ("EMP-DEMO-ADMIN", "Aditi Sharma", "admin@ethara.ai", "Admin@123", UserRole.ADMIN, "ENG", "Principal Engineer"),
            ("EMP-DEMO-HR", "Rohan Mehta", "hr@ethara.ai", "HrDemo@123", UserRole.HR, "HR", "HR Manager"),
            ("EMP-DEMO-PM", "Kavya Iyer", "pm@ethara.ai", "PmDemo@123", UserRole.PROJECT_MANAGER, "PRD", "Senior Product Manager"),
            ("EMP-DEMO-EMP", "Arjun Nair", "employee@ethara.ai", "EmpDemo@123", UserRole.EMPLOYEE, "ENG", "Software Engineer II"),
        ]
        demo_ids = []
        for code, name, email, password, role, dept_code, designation in demo_accounts:
            eid = uuid.uuid4()
            demo_ids.append(eid)
            employee_rows.append(
                {
                    "id": eid,
                    "employee_code": code,
                    "full_name": name,
                    "email": email,
                    "hashed_password": hash_password(password),
                    "role": role,
                    "department_id": dept_ids_by_code[dept_code],
                    "designation": designation,
                    "manager_id": None,
                    "employment_status": EmploymentStatus.ACTIVE,
                    "date_of_joining": today_minus(random.randint(200, 1500)),
                    "location": random.choice(LOCATIONS),
                    "is_active": True,
                }
            )

        # 3b. Leadership tier (no manager) — top of the org chart.
        leadership_ids_by_dept: dict[str, list[uuid.UUID]] = {c: [] for c in dept_codes}
        leadership_count = 60
        for i in range(leadership_count):
            dept_code = dept_codes[i % len(dept_codes)]
            eid = uuid.uuid4()
            leadership_ids_by_dept[dept_code].append(eid)
            employee_rows.append(
                {
                    "id": eid,
                    "employee_code": f"EMP{i + 1:05d}",
                    "full_name": fake.name(),
                    "email": f"leader{i + 1}.{dept_code.lower()}@ethara.ai",
                    "hashed_password": SHARED_PASSWORD_HASH,
                    "role": UserRole.EMPLOYEE,
                    "department_id": dept_ids_by_code[dept_code],
                    "designation": DESIGNATIONS_BY_DEPT[dept_code][-1],
                    "manager_id": None,
                    "employment_status": EmploymentStatus.ACTIVE,
                    "date_of_joining": today_minus(random.randint(1000, 2500)),
                    "location": random.choice(LOCATIONS),
                    "is_active": True,
                }
            )

        # 3c. Project managers — will be linked 1:1 to projects below.
        pm_ids = []
        for i in range(NUM_PROJECTS):
            dept_code = "PRD" if i % 3 == 0 else random.choice(dept_codes)
            eid = uuid.uuid4()
            pm_ids.append(eid)
            manager_pool = leadership_ids_by_dept[dept_code] or [None]
            employee_rows.append(
                {
                    "id": eid,
                    "employee_code": f"EMP{leadership_count + i + 1:05d}",
                    "full_name": fake.name(),
                    "email": f"pm{i + 1}.{dept_code.lower()}@ethara.ai",
                    "hashed_password": SHARED_PASSWORD_HASH,
                    "role": UserRole.PROJECT_MANAGER,
                    "department_id": dept_ids_by_code[dept_code],
                    "designation": "Project Manager",
                    "manager_id": random.choice(manager_pool),
                    "employment_status": EmploymentStatus.ACTIVE,
                    "date_of_joining": today_minus(random.randint(500, 2000)),
                    "location": random.choice(LOCATIONS),
                    "is_active": True,
                }
            )

        # 3d. A handful of dedicated HR + Admin accounts beyond the demo ones.
        for i in range(11):
            eid = uuid.uuid4()
            employee_rows.append(
                {
                    "id": eid,
                    "employee_code": f"EMP{leadership_count + NUM_PROJECTS + i + 1:05d}",
                    "full_name": fake.name(),
                    "email": f"hrstaff{i + 1}@ethara.ai",
                    "hashed_password": SHARED_PASSWORD_HASH,
                    "role": UserRole.HR,
                    "department_id": dept_ids_by_code["HR"],
                    "designation": random.choice(DESIGNATIONS_BY_DEPT["HR"]),
                    "manager_id": random.choice(leadership_ids_by_dept["HR"]) if leadership_ids_by_dept["HR"] else None,
                    "employment_status": EmploymentStatus.ACTIVE,
                    "date_of_joining": today_minus(random.randint(300, 1800)),
                    "location": random.choice(LOCATIONS),
                    "is_active": True,
                }
            )
        for i in range(2):
            eid = uuid.uuid4()
            employee_rows.append(
                {
                    "id": eid,
                    "employee_code": f"EMP{leadership_count + NUM_PROJECTS + 11 + i + 1:05d}",
                    "full_name": fake.name(),
                    "email": f"adminstaff{i + 1}@ethara.ai",
                    "hashed_password": SHARED_PASSWORD_HASH,
                    "role": UserRole.ADMIN,
                    "department_id": dept_ids_by_code["ENG"],
                    "designation": "IT Administrator",
                    "manager_id": None,
                    "employment_status": EmploymentStatus.ACTIVE,
                    "date_of_joining": today_minus(random.randint(300, 1800)),
                    "location": random.choice(LOCATIONS),
                    "is_active": True,
                }
            )

        # 3e. Rank-and-file employees — the bulk of the 5,000.
        all_manager_candidates = [r["id"] for r in employee_rows]  # leadership + PMs + HR/admin seeded so far
        remaining = TOTAL_EMPLOYEES - len(employee_rows)
        status_weights = [88, 5, 4, 3]  # active, on_leave, terminated, notice_period
        statuses = list(EmploymentStatus)

        rank_and_file_start_index = len(employee_rows)
        for i in range(remaining):
            dept_code = random.choice(dept_codes)
            eid = uuid.uuid4()
            doj = today_minus(random.randint(1, 1800))
            # Managers are drawn from leadership/PM/HR pool + any earlier
            # rank-and-file employee already generated in this loop, so the
            # org chart has realistic multi-level depth without forward
            # references (a manager always already exists by the time a
            # report is created).
            manager_pool = leadership_ids_by_dept[dept_code] or all_manager_candidates
            employee_rows.append(
                {
                    "id": eid,
                    "employee_code": f"EMP{len(employee_rows) + 1:05d}",
                    "full_name": fake.name(),
                    "email": f"{fake.user_name()}{i}@ethara.ai",  # index suffix guarantees uniqueness at this volume
                    "hashed_password": SHARED_PASSWORD_HASH,
                    "role": UserRole.EMPLOYEE,
                    "department_id": dept_ids_by_code[dept_code],
                    "designation": random.choice(DESIGNATIONS_BY_DEPT[dept_code][:-1]),
                    "manager_id": random.choice(manager_pool),
                    "employment_status": random.choices(statuses, weights=status_weights, k=1)[0],
                    "date_of_joining": doj,
                    "location": random.choice(LOCATIONS),
                    "is_active": True,
                }
            )
            # Occasionally let a freshly created employee become a manager
            # candidate for subsequent employees too — keeps hierarchy from
            # being flat with 4,900 people all reporting to 60 leaders.
            if i % 15 == 0:
                all_manager_candidates.append(eid)

        for i in range(0, len(employee_rows), CHUNK_SIZE):
            await session.execute(insert(Employee), employee_rows[i : i + CHUNK_SIZE])
        print(f"Seeded {len(employee_rows)} employees")

        # --- 4. Projects ---
        project_rows = []
        used_codes = set()
        for i in range(NUM_PROJECTS):
            word = PROJECT_CODE_WORDS[i % len(PROJECT_CODE_WORDS)]
            code = f"PRJ-{word.upper()}-{i + 1:03d}"
            used_codes.add(code)
            is_active = random.random() > 0.15  # ~85% of projects currently active
            start = today_minus(random.randint(60, 1500))
            end = None if is_active else today_minus(random.randint(1, 59))
            project_rows.append(
                {
                    "id": uuid.uuid4(),
                    "name": f"{word} {random.choice(['Platform', 'Migration', 'Revamp', 'Initiative', 'Suite', 'Rollout'])}",
                    "code": code,
                    "client": random.choice(CLIENTS),
                    "manager_id": pm_ids[i],
                    "team_size_target": random.randint(15, 120),
                    "start_date": start,
                    "end_date": end,
                    "is_active": is_active,
                }
            )
        await session.execute(insert(Project), project_rows)
        print(f"Seeded {len(project_rows)} projects")

        # --- 5. Project assignments (~90% of employees get an active one) ---
        assignable_employees = [r for r in employee_rows if r["role"] == UserRole.EMPLOYEE]
        random.shuffle(assignable_employees)
        assign_count = int(len(assignable_employees) * 0.90)
        assignment_rows = []
        for emp in assignable_employees[:assign_count]:
            project = random.choice(project_rows)
            start = max(emp["date_of_joining"], project["start_date"])
            assignment_rows.append(
                {
                    "id": uuid.uuid4(),
                    "employee_id": emp["id"],
                    "project_id": project["id"],
                    "start_date": start,
                    "end_date": None,
                }
            )
        for i in range(0, len(assignment_rows), CHUNK_SIZE):
            await session.execute(insert(ProjectAssignment), assignment_rows[i : i + CHUNK_SIZE])
        print(f"Seeded {len(assignment_rows)} active project assignments "
              f"({len(assignable_employees) - assign_count} employees left on bench, unassigned)")

        # --- 6. Seat allocations (~90% of ALL employees, including PM/HR/Admin/demo) ---
        allocatable_employees = [r for r in employee_rows]
        random.shuffle(allocatable_employees)
        seat_pool = seat_rows.copy()
        random.shuffle(seat_pool)

        allocate_count = min(int(len(allocatable_employees) * 0.90), len(seat_pool) - 100)
        allocation_rows = []
        occupied_seat_ids = set()
        for idx in range(allocate_count):
            emp = allocatable_employees[idx]
            seat = seat_pool[idx]
            occupied_seat_ids.add(seat["id"])
            allocation_date = max(emp["date_of_joining"], today_minus(random.randint(0, 600)))
            allocation_rows.append(
                {
                    "id": uuid.uuid4(),
                    "seat_id": seat["id"],
                    "employee_id": emp["id"],
                    "event_type": AllocationEventType.ALLOCATE,
                    "allocation_date": allocation_date,
                    "release_date": None,
                }
            )
        for i in range(0, len(allocation_rows), CHUNK_SIZE):
            await session.execute(insert(SeatAllocation), allocation_rows[i : i + CHUNK_SIZE])

        # Mark those seats OCCUPIED, plus a handful of RESERVED / OUT_OF_SERVICE
        # among the remaining vacant seats for dashboard realism.
        remaining_seats = [s for s in seat_pool if s["id"] not in occupied_seat_ids]
        random.shuffle(remaining_seats)
        reserved_slice = remaining_seats[:150]
        out_of_service_slice = remaining_seats[150:200]

        from sqlalchemy import update as sa_update

        for i in range(0, len(seat_rows), CHUNK_SIZE):
            chunk = seat_rows[i : i + CHUNK_SIZE]
            for s in chunk:
                if s["id"] in occupied_seat_ids:
                    s["status"] = SeatStatus.OCCUPIED
            occ_ids = [s["id"] for s in chunk if s["id"] in occupied_seat_ids]
            if occ_ids:
                await session.execute(
                    sa_update(Seat).where(Seat.id.in_(occ_ids)).values(status=SeatStatus.OCCUPIED)
                )
        reserved_ids = [s["id"] for s in reserved_slice]
        if reserved_ids:
            await session.execute(sa_update(Seat).where(Seat.id.in_(reserved_ids)).values(status=SeatStatus.RESERVED))
        oos_ids = [s["id"] for s in out_of_service_slice]
        if oos_ids:
            await session.execute(sa_update(Seat).where(Seat.id.in_(oos_ids)).values(status=SeatStatus.OUT_OF_SERVICE))

        print(f"Seeded {len(allocation_rows)} seat allocations "
              f"({len(reserved_ids)} reserved, {len(oos_ids)} out of service, "
              f"{len(seat_rows) - len(occupied_seat_ids) - len(reserved_ids) - len(oos_ids)} vacant)")

        await session.commit()

    await engine.dispose()
    print("\nSeed complete.")
    print("Demo login credentials (all roles):")
    for code, name, email, password, role, *_ in demo_accounts:
        print(f"  {role.value:<16} {email:<20} / {password}")
    print("\nAll other seeded employees share password: Password123!")


if __name__ == "__main__":
    asyncio.run(seed())
