import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee, require_role
from app.core.security import hash_password
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.models.enums import UserRole
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeePage, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["Employees"])

# Admin + HR can write; every authenticated role can read (Employee role is
# further restricted to read-only by simply never being granted the write
# dependency below — PMs get read access here too, and are scoped to their
# own project's roster at the frontend/query-filter level, not blocked
# entirely from this endpoint).
WRITE_ROLES = require_role(UserRole.ADMIN, UserRole.HR)


@router.get("", response_model=EmployeePage)
async def list_employees(
    q: str | None = Query(None, description="Search by name, employee code, or email"),
    department_id: uuid.UUID | None = None,
    employment_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    repo = EmployeeRepository(db)
    rows, total = await repo.search(
        query=q, department_id=department_id, employment_status=employment_status, page=page, page_size=page_size
    )
    return EmployeePage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/without-seat", response_model=EmployeePage)
async def employees_without_seat(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    repo = EmployeeRepository(db)
    rows, total = await repo.get_without_active_seat(page=page, page_size=page_size)
    return EmployeePage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    repo = EmployeeRepository(db)
    employee = await repo.get_by_id(employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    repo = EmployeeRepository(db)
    if await repo.get_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    if await repo.get_by_code(payload.employee_code) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Employee code already exists")

    data = payload.model_dump(exclude={"password"})
    employee = EmployeeModel(**data, hashed_password=hash_password(payload.password))
    employee = await repo.create(employee)
    await repo.commit()
    return employee


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    repo = EmployeeRepository(db)
    employee = await repo.get_by_id(employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    await repo.commit()
    await db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(require_role(UserRole.ADMIN)),
):
    """Admin-only, and a soft delete (is_active=False) rather than a hard
    DELETE — an offboarded employee's seat/project history should remain
    queryable for reporting (dashboard 'Recent Releases', audit trail)."""
    repo = EmployeeRepository(db)
    employee = await repo.get_by_id(employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    employee.is_active = False
    await repo.commit()
