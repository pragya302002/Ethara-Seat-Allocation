import pytest

pytestmark = pytest.mark.asyncio


async def _admin_token(client, admin_employee) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": admin_employee.email, "password": "TestPass123!"}
    )
    return resp.json()["access_token"]


async def test_allocate_seat_success(client, admin_employee, employee_without_seat, vacant_seat):
    token = await _admin_token(client, admin_employee)
    resp = await client.post(
        "/api/v1/seats/allocate",
        headers={"Authorization": f"Bearer {token}"},
        json={"seat_id": str(vacant_seat.id), "employee_id": str(employee_without_seat.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["seat_id"] == str(vacant_seat.id)
    assert data["release_date"] is None


async def test_allocate_already_occupied_seat_returns_409(
    client, admin_employee, employee_without_seat, vacant_seat, db_session
):
    """Covers the DB-constraint-backed concurrency safety documented in
    seat_service.py: a seat that already has an active allocation must be
    rejected with 409, not silently double-booked."""
    token = await _admin_token(client, admin_employee)

    first = await client.post(
        "/api/v1/seats/allocate",
        headers={"Authorization": f"Bearer {token}"},
        json={"seat_id": str(vacant_seat.id), "employee_id": str(employee_without_seat.id)},
    )
    assert first.status_code == 201

    # A second, different employee, same seat. Uses a fresh short-lived
    # session rather than the shared db_session fixture — interleaving
    # fixture-session writes with real HTTP calls (which open their own
    # sessions via get_db) left the shared connection's transaction state
    # inconsistent in practice; a dedicated session avoids that entirely.
    import uuid
    from datetime import date
    from app.core.security import hash_password
    from app.database.session import AsyncSessionLocal
    from app.models.employee import Employee
    from app.models.enums import EmploymentStatus, UserRole

    second_employee = Employee(
        id=uuid.uuid4(),
        employee_code=f"TEST-EMP2-{uuid.uuid4().hex[:6]}",
        full_name="Second Employee",
        email=f"second.{uuid.uuid4().hex[:8]}@etharatest-qa.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE,
        designation="Engineer",
        employment_status=EmploymentStatus.ACTIVE,
        date_of_joining=date.today(),
        is_active=True,
    )
    async with AsyncSessionLocal() as tmp_session:
        tmp_session.add(second_employee)
        await tmp_session.commit()

    second = await client.post(
        "/api/v1/seats/allocate",
        headers={"Authorization": f"Bearer {token}"},
        json={"seat_id": str(vacant_seat.id), "employee_id": str(second_employee.id)},
    )
    assert second.status_code == 409


async def test_release_then_reallocate(client, admin_employee, employee_without_seat, vacant_seat):
    """Allocate -> release -> the same seat becomes allocatable again."""
    token = await _admin_token(client, admin_employee)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/seats/allocate",
        headers=headers,
        json={"seat_id": str(vacant_seat.id), "employee_id": str(employee_without_seat.id)},
    )
    release = await client.post(
        "/api/v1/seats/release", headers=headers, json={"seat_id": str(vacant_seat.id)}
    )
    assert release.status_code == 200
    assert release.json()["release_date"] is not None

    reallocate = await client.post(
        "/api/v1/seats/allocate",
        headers=headers,
        json={"seat_id": str(vacant_seat.id), "employee_id": str(employee_without_seat.id)},
    )
    assert reallocate.status_code == 201


async def test_allocate_to_employee_who_already_has_a_seat_returns_409(
    client, admin_employee, employee_without_seat, vacant_seat, db_session
):
    """An employee can't hold two active seats at once — must use transfer."""
    token = await _admin_token(client, admin_employee)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/seats/allocate",
        headers=headers,
        json={"seat_id": str(vacant_seat.id), "employee_id": str(employee_without_seat.id)},
    )

    from app.models.seat import Seat
    from app.models.enums import SeatType, SeatStatus
    from app.database.session import AsyncSessionLocal
    import uuid

    second_seat = Seat(
        seat_number=f"TEST-2-{uuid.uuid4().hex[:6]}",
        zone_id=vacant_seat.zone_id,
        seat_type=SeatType.STANDARD,
        status=SeatStatus.VACANT,
    )
    async with AsyncSessionLocal() as tmp_session:
        tmp_session.add(second_seat)
        await tmp_session.commit()
        await tmp_session.refresh(second_seat)

    resp = await client.post(
        "/api/v1/seats/allocate",
        headers=headers,
        json={"seat_id": str(second_seat.id), "employee_id": str(employee_without_seat.id)},
    )
    assert resp.status_code == 409
