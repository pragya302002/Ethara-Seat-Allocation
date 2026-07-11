import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import EmploymentStatus, UserRole


class EmployeeBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    department_id: uuid.UUID | None = None
    designation: str = Field(min_length=1, max_length=120)
    manager_id: uuid.UUID | None = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    date_of_joining: date
    location: str | None = None
    role: UserRole = UserRole.EMPLOYEE


class EmployeeCreate(EmployeeBase):
    employee_code: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=8, description="Plaintext, hashed server-side before storage")


class EmployeeUpdate(BaseModel):
    """All fields optional — PATCH semantics, only supplied fields are updated."""
    full_name: str | None = None
    department_id: uuid.UUID | None = None
    designation: str | None = None
    manager_id: uuid.UUID | None = None
    employment_status: EmploymentStatus | None = None
    location: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeePage(BaseModel):
    items: list[EmployeeOut]
    total: int
    page: int
    page_size: int
