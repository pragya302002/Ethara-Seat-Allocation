from datetime import date, datetime
import uuid

from pydantic import BaseModel

from app.schemas.seat import OccupancySummary


class DepartmentCount(BaseModel):
    department: str
    count: int


class ProjectCount(BaseModel):
    project: str
    count: int


class FloorUtilization(BaseModel):
    building: str
    floor: int
    total_seats: int
    occupied_seats: int
    utilization_percent: float


class RecentAllocationItem(BaseModel):
    id: uuid.UUID
    seat_id: uuid.UUID
    employee_id: uuid.UUID
    event_type: str
    allocation_date: date
    release_date: date | None


class DashboardSummary(BaseModel):
    total_employees: int
    new_joiners_last_30_days: int
    occupancy: OccupancySummary
    department_wise: list[DepartmentCount]
    project_wise: list[ProjectCount]
    floor_utilization: list[FloorUtilization]
    recent_allocations: list[RecentAllocationItem]
    recent_releases: list[RecentAllocationItem]
