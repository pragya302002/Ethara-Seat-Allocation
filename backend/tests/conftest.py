"""
Test fixtures.

Uses the same local Postgres the app runs against (not sqlite) — the
schema relies on Postgres-specific features (partial unique indexes,
UUID columns) that sqlite can't express, so testing against sqlite would
validate a different set of constraints than what actually runs in
production. Each test runs inside a transaction that's rolled back at
teardown, so tests don't pollute each other or require reseeding.
"""
import asyncio
import uuid
from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal, engine
from app.main import app
from app.models import Base
from app.models.employee import Employee
from app.models.enums import EmploymentStatus, UserRole
from app.models.location import Building, Floor, Zone
from app.models.seat import Seat
from app.models.enums import SeatStatus, SeatType


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    """Without this, SQLAlchemy's connection pool can hand a test a
    pooled asyncpg connection that was opened under a *previous* test's
    event loop, which asyncpg refuses to operate on ('Future attached to
    a different loop'). Disposing after every test forces a fresh
    connection under the current loop. Slower than ideal for a large
    suite, but correct — and this suite is small enough that the cost is
    negligible."""
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_employee(db_session: AsyncSession):
    emp = Employee(
        id=uuid.uuid4(),
        employee_code=f"TEST-ADMIN-{uuid.uuid4().hex[:6]}",
        full_name="Test Admin",
        email=f"test.admin.{uuid.uuid4().hex[:8]}@etharatest-qa.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.ADMIN,
        designation="QA Engineer",
        employment_status=EmploymentStatus.ACTIVE,
        date_of_joining=date.today(),
        is_active=True,
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    yield emp


@pytest_asyncio.fixture
async def employee_without_seat(db_session: AsyncSession):
    emp = Employee(
        id=uuid.uuid4(),
        employee_code=f"TEST-EMP-{uuid.uuid4().hex[:6]}",
        full_name="Test Employee",
        email=f"test.employee.{uuid.uuid4().hex[:8]}@etharatest-qa.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE,
        designation="QA Engineer",
        employment_status=EmploymentStatus.ACTIVE,
        date_of_joining=date.today(),
        is_active=True,
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    yield emp


@pytest_asyncio.fixture
async def vacant_seat(db_session: AsyncSession):
    building = Building(name=f"Test Building {uuid.uuid4().hex[:6]}")
    db_session.add(building)
    await db_session.flush()
    floor = Floor(building_id=building.id, floor_number=1, name="Floor 1")
    db_session.add(floor)
    await db_session.flush()
    zone = Zone(floor_id=floor.id, name=f"Test Zone {uuid.uuid4().hex[:6]}")
    db_session.add(zone)
    await db_session.flush()
    seat = Seat(
        seat_number=f"TEST-{uuid.uuid4().hex[:6]}",
        zone_id=zone.id,
        seat_type=SeatType.STANDARD,
        status=SeatStatus.AVAILABLE,
    )
    db_session.add(seat)
    await db_session.commit()
    await db_session.refresh(seat)
    yield seat
