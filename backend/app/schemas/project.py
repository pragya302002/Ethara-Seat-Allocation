import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=30)
    client: str = Field(min_length=1, max_length=150)
    manager_id: uuid.UUID | None = None
    team_size_target: int = Field(ge=0, default=0)
    start_date: date
    end_date: date | None = None
    is_active: bool = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    client: str | None = None
    manager_id: uuid.UUID | None = None
    team_size_target: int | None = None
    end_date: date | None = None
    is_active: bool | None = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    total: int
    page: int
    page_size: int


class ProjectAssignRequest(BaseModel):
    employee_id: uuid.UUID
    start_date: date | None = None


class ProjectAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    employee_id: uuid.UUID
    project_id: uuid.UUID
    start_date: date
    end_date: date | None
