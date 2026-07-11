import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SeatStatus, SeatType


class SeatCreate(BaseModel):
    seat_number: str
    zone_id: uuid.UUID
    bay: str | None = None
    row_label: str | None = None
    seat_type: SeatType = SeatType.STANDARD
    status: SeatStatus = SeatStatus.AVAILABLE


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seat_number: str
    zone_id: uuid.UUID
    bay: str | None
    row_label: str | None
    seat_type: SeatType
    status: SeatStatus
    # Computed at query time via join (not stored columns) — see
    # seat_repository.py list_all(). Kept as a join rather than a
    # denormalized FK because it's derived from the same active
    # SeatAllocation/ProjectAssignment rows that are already the source of
    # truth for "who sits here" and "what project are they on" — a third
    # copy of that fact would be one more place for it to drift out of sync.
    allocated_employee_name: str | None = None
    allocated_project_name: str | None = None
    allocation_date: date | None = None
    zone_name: str | None = None
    floor_number: int | None = None
    building_name: str | None = None


class SeatPage(BaseModel):
    items: list[SeatOut]
    total: int
    page: int
    page_size: int


class SeatAllocationRequest(BaseModel):
    seat_id: uuid.UUID
    employee_id: uuid.UUID
    allocation_date: date | None = None  # defaults to today in service layer


class SeatReleaseRequest(BaseModel):
    seat_id: uuid.UUID
    release_date: date | None = None


class SeatTransferRequest(BaseModel):
    employee_id: uuid.UUID
    new_seat_id: uuid.UUID
    transfer_date: date | None = None


class SeatAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seat_id: uuid.UUID
    employee_id: uuid.UUID
    event_type: str
    allocation_date: date
    release_date: date | None


class OccupancySummary(BaseModel):
    available: int
    occupied: int
    reserved: int
    maintenance: int
    total: int
    utilization_percent: float


class SeatSuggestionOut(BaseModel):
    """Response for the proximity-based new-joiner seat suggestion endpoint."""
    suggested_seats: list[SeatOut]
    suggestion_basis: str  # e.g. "same zone as project teammates" or "no teammates seated yet — showing all available seats"
