import pytest

pytestmark = pytest.mark.asyncio


async def test_login_success(client, admin_employee):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": admin_employee.email, "password": "TestPass123!"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert "access_token" in data


async def test_login_wrong_password(client, admin_employee):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": admin_employee.email, "password": "WrongPassword"}
    )
    assert resp.status_code == 401


async def test_login_nonexistent_email_same_error_as_wrong_password(client):
    """Regression guard for the enumeration-safety decision documented in
    auth_service.py — both failure modes must return an identical error."""
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@etharatest-qa.com", "password": "whatever"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


async def test_protected_endpoint_requires_token(client):
    resp = await client.get("/api/v1/employees")
    assert resp.status_code == 401


async def test_employee_role_cannot_create_employee(client, db_session):
    """RBAC guard: EMPLOYEE role must not be able to hit WRITE_ROLES-gated endpoints."""
    from datetime import date
    import uuid
    from app.core.security import hash_password
    from app.models.employee import Employee
    from app.models.enums import EmploymentStatus, UserRole

    plain_employee = Employee(
        id=uuid.uuid4(),
        employee_code=f"TEST-PLAIN-{uuid.uuid4().hex[:6]}",
        full_name="Plain Employee",
        email=f"plain.{uuid.uuid4().hex[:8]}@etharatest-qa.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE,
        designation="Engineer",
        employment_status=EmploymentStatus.ACTIVE,
        date_of_joining=date.today(),
        is_active=True,
    )
    db_session.add(plain_employee)
    await db_session.commit()

    login = await client.post(
        "/api/v1/auth/login", json={"email": plain_employee.email, "password": "TestPass123!"}
    )
    token = login.json()["access_token"]

    resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Should Fail",
            "email": "shouldfail@etharatest-qa.com",
            "employee_code": "SHOULDFAIL01",
            "designation": "Engineer",
            "date_of_joining": "2026-01-01",
            "password": "SomePass123!",
        },
    )
    assert resp.status_code == 403
