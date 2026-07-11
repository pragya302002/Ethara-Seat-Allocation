"""
Seed script — generates a realistic ~5,000 employee dataset.

Run with: python -m app.seed.seed

Performance notes (why this looks different from typical "create N rows"
scripts):
1. Passwords: bcrypt-hashing a unique password per row for 5,000 rows would
   take tens of minutes (bcrypt is deliberately slow). Every seeded account
   shares ONE pre-hashed demo password. This is a seed-data-only shortcut —
   documented here and in the README — never acceptable for real user data.
2. Bulk writes: rows are built in memory and flushed in batches (not one
   commit per row), which is the difference between seeding in ~1-2 minutes
   vs. 20+ minutes over a network connection to Railway.
3. Deterministic-ish structure: office hierarchy (buildings/floors/zones/
   seats) is generated first and sized to comfortably exceed 5,000 seats,
   so seat allocation for employees never runs out of vacant seats.
"""
import asyncio
import random
import uuid
from datetime import date, timedelta

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal, engine
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

fake = Faker()
Faker.seed(42)
random.seed(42)

TOTAL_EMPLOYEES = 5000
SEAT_FILL_RATE = 0.88  # ~12% of employees are "new joiners" without a seat yet
PROJECT_FILL_RATE = 0.82  # ~18% unassigned / bench

DEMO_PASSWORD_HASH = hash_password("Password123!")  # shared across all seed accounts — see module docstring

DEPARTMENTS = [
    ("Engineering", "ENG"), ("Data Science", "DS"), ("Product", "PRD"),
    ("Design", "DSG"), ("Quality Assurance", "QA"), ("DevOps", "DEVOPS"),
    ("Human Resources", "HR"), ("Finance", "FIN"), ("Sales", "SALES"),
    ("Marketing", "MKT"), ("Customer Success", "CS"), ("Legal", "LEGAL"),
    ("IT Support", "ITS"), ("Operations", "OPS"),
]

DESIGNATIONS_BY_DEPT = {
    "ENG": ["Software Engineer I", "Software Engineer II", "Senior Software Engineer", "Staff Engineer", "Engineering Manager"],
    "DS": ["Data Analyst", "Data Scientist", "Senior Data Scientist", "ML Engineer", "AI Engineer"],
    "PRD": ["Associate Product Manager", "Product Manager", "Senior Product Manager"],
    "DSG": ["UI/UX Designer", "Senior Product Designer", "Design Lead"],
    "QA": ["QA Engineer", "Senior QA Engineer", "SDET"],
    "DEVOPS": ["DevOps Engineer", "Site Reliability Engineer", "Cloud Infrastructure Engineer"],
    "HR": ["HR Executive", "HR Business Partner", "Talent Acquisition Specialist"],
    "FIN": ["Financial Analyst", "Accounts Executive", "Finance Manager"],
    "SALES": ["Sales Executive", "Account Executive", "Sales Manager"],
    "MKT": ["Marketing Executive", "Content Strategist", "Marketing Manager"],
    "CS": ["Customer Success Associate", "Customer Success Manager"],
    "LEGAL": ["Legal Associate", "Compliance Officer"],
    "ITS": ["IT Support Engineer", "Systems Administrator"],
    "OPS": ["Operations Executive", "Operations Manager"],
}

CLIENTS = ["Acme Corp", "Globex Industries", "Initech", "Umbrella Retail", "Stark Logistics",
           "Wayne Financial", "Wonka Foods", "Hooli Tech", "Vandelay Imports", "Soylent Health"]

BUILDINGS = ["Tower A", "Tower B"]
FLOORS_PER_BUILDING = 6
ZONES_PER_FLOOR = ["Zone North", "Zone South", "Zone East", "Zone West"]
# 2 buildings * 6 floors * 4 zones = 48 zones. Target: comfortably exceed
# TOTAL_EMPLOYEES so SEAT_FILL_RATE actually reaches its intended
# percentage instead of being silently capped by seat scarcity.
# 48 zones * 115 seats/zone = 5,520 seats (~10% more than 5,000 employees,
# leaving genuine vacant capacity for the "vacant seats" dashboard/search
# features to have something to show).
SEATS_PER_ZONE = 115


async def seed_departments(db: AsyncSession) -> dict[str, Department]:
    depts = {}
    for name, code in DEPARTMENTS:
        d = Department(name=name, code=code)
        db.add(d)
        depts[code] = d
    await db.flush()
    return depts


async def seed_office_hierarchy(db: AsyncSession) -> list[Seat]:
    seats: list[Seat] = []
    for b_name in BUILDINGS:
        building = Building(name=b_name, address=fake.address())
        db.add(building)
        await db.flush()

        for floor_num in range(1, FLOORS_PER_BUILDING + 1):
            floor = Floor(building_id=building.id, floor_number=floor_num, name=f"Floor {floor_num}")
            db.add(floor)
            await db.flush()

            for zone_name in ZONES_PER_FLOOR:
                zone = Zone(floor_id=floor.id, name=zone_name)
                db.add(zone)
                await db.flush()

                for i in range(1, SEATS_PER_ZONE + 1):
                    seat_type = random.choices(
                        list(SeatType), weights=[75, 10, 8, 5, 2], k=1
                    )[0]
                    seat = Seat(
                        seat_number=f"{zone_name[5:8].upper()}-{i:03d}",
                        zone_id=zone.id,
                        row_label=str((i - 1) // 10 + 1),
                        seat_type=seat_type,
                        status=SeatStatus.VACANT,
                    )
                    seats.append(seat)
    db.add_all(seats)
    await db.flush()
    print(f"Seeded {len(seats)} seats across {len(BUILDINGS)} buildings.")
    return seats


def random_join_date() -> date:
    days_ago = random.randint(30, 365 * 6)  # up to 6 years tenure
    return date.today() - timedelta(days=days_ago)


async def seed_employees(db: AsyncSession, depts: dict[str, Department]) -> list[Employee]:
    employees: list[Employee] = []
    used_emails: set[str] = set()

    for i in range(1, TOTAL_EMPLOYEES + 1):
        dept_code = random.choice(list(depts.keys()))
        dept = depts[dept_code]
        designation = random.choice(DESIGNATIONS_BY_DEPT[dept_code])

        first, last = fake.first_name(), fake.last_name()
        base_email = f"{first}.{last}{i}".lower().replace(" ", "")
        email = f"{base_email}@etharatest.com"
        while email in used_emails:
            email = f"{base_email}{random.randint(1,999)}@etharatest.com"
        used_emails.add(email)

        role = UserRole.EMPLOYEE
        if i == 1:
            role = UserRole.ADMIN  # first seeded account is a guaranteed admin login
        elif i % 200 == 0:
            role = UserRole.HR
        elif i % 150 == 0:
            role = UserRole.PROJECT_MANAGER

        status = random.choices(
            list(EmploymentStatus), weights=[90, 5, 2, 3], k=1
        )[0]

        emp = Employee(
            id=uuid.uuid4(),
            employee_code=f"EMP{i:05d}",
            full_name=f"{first} {last}",
            email=email,
            hashed_password=DEMO_PASSWORD_HASH,
            role=role,
            department_id=dept.id,
            designation=designation,
            manager_id=None,  # assigned in a second pass below
            employment_status=status,
            date_of_joining=random_join_date(),
            location=random.choice(["Bengaluru", "Gurugram", "Pune", "Hyderabad"]),
            is_active=status != EmploymentStatus.TERMINATED,
        )
        employees.append(emp)

    db.add_all(employees)
    await db.flush()
    print(f"Seeded {len(employees)} employees.")

    # Second pass: assign each employee a random manager from a more senior
    # designation pool, skipping self-reference. Kept simple (random senior
    # peer) rather than a strict org tree — sufficient for demo/search
    # purposes without the complexity of guaranteeing an acyclic hierarchy.
    senior_titles = {"Senior", "Manager", "Lead", "Staff", "Principal"}
    seniors = [e for e in employees if any(t in e.designation for t in senior_titles)]
    for emp in employees:
        if seniors and emp not in seniors:
            candidate = random.choice(seniors)
            if candidate.id != emp.id:
                emp.manager_id = candidate.id
    await db.flush()

    return employees


async def seed_projects(db: AsyncSession, employees: list[Employee]) -> list[Project]:
    managers_pool = [e for e in employees if e.role == UserRole.PROJECT_MANAGER] or employees[:20]
    projects = []
    project_names = [
        "Atlas", "Phoenix", "Nova", "Zenith", "Orion", "Titan", "Nimbus", "Vertex",
        "Quantum", "Horizon", "Catalyst", "Meridian", "Pulse", "Fusion", "Apex",
        "Beacon", "Cascade", "Ember", "Frontier", "Halo",
    ]
    for idx, name in enumerate(project_names, start=1):
        manager = random.choice(managers_pool)
        start = date.today() - timedelta(days=random.randint(30, 900))
        is_active = random.random() < 0.8
        project = Project(
            name=f"Project {name}",
            code=f"PRJ-{idx:03d}",
            client=random.choice(CLIENTS),
            manager_id=manager.id,
            team_size_target=random.randint(5, 40),
            start_date=start,
            end_date=None if is_active else start + timedelta(days=random.randint(60, 400)),
            is_active=is_active,
        )
        projects.append(project)
    db.add_all(projects)
    await db.flush()
    print(f"Seeded {len(projects)} projects.")
    return projects


async def seed_project_assignments(db: AsyncSession, employees: list[Employee], projects: list[Project]) -> None:
    active_projects = [p for p in projects if p.is_active] or projects
    assign_count = int(len(employees) * PROJECT_FILL_RATE)
    chosen = random.sample(employees, assign_count)

    assignments = []
    for emp in chosen:
        project = random.choice(active_projects)
        start = max(emp.date_of_joining, project.start_date) + timedelta(days=random.randint(0, 30))
        assignments.append(
            ProjectAssignment(employee_id=emp.id, project_id=project.id, start_date=start, end_date=None)
        )
    db.add_all(assignments)
    await db.flush()
    print(f"Seeded {len(assignments)} active project assignments.")


async def seed_seat_allocations(db: AsyncSession, employees: list[Employee], seats: list[Seat]) -> None:
    active_employees = [e for e in employees if e.employment_status != EmploymentStatus.TERMINATED]
    fill_count = min(int(len(employees) * SEAT_FILL_RATE), len(seats), len(active_employees))
    chosen_employees = random.sample(active_employees, fill_count)
    chosen_seats = random.sample(seats, fill_count)

    allocations = []
    for emp, seat in zip(chosen_employees, chosen_seats):
        alloc_date = emp.date_of_joining + timedelta(days=random.randint(0, 5))
        allocations.append(
            SeatAllocation(
                seat_id=seat.id,
                employee_id=emp.id,
                event_type=AllocationEventType.ALLOCATE,
                allocation_date=alloc_date,
                release_date=None,
            )
        )
        seat.status = SeatStatus.OCCUPIED
    db.add_all(allocations)
    await db.flush()
    print(f"Seeded {len(allocations)} active seat allocations "
          f"({len(employees) - fill_count} employees left seatless as 'new joiners').")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(Employee.id).limit(1))).first()
        if existing:
            print("Employees already exist — aborting to avoid duplicate seeding. "
                  "Drop and re-migrate the DB first if you want a fresh seed.")
            return

        depts = await seed_departments(db)
        seats = await seed_office_hierarchy(db)
        employees = await seed_employees(db, depts)
        projects = await seed_projects(db, employees)
        await seed_project_assignments(db, employees, projects)
        await seed_seat_allocations(db, employees, seats)

        await db.commit()
        print("\nSeed complete.")
        print(f"Admin login -> email: {employees[0].email} / password: Password123!")


if __name__ == "__main__":
    asyncio.run(main())
