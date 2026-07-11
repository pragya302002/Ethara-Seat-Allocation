import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SeatStatus, SeatType


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seat_number: str
    zone_id: uuid.UUID
    row_label: str | None
    seat_type: SeatType
    status: SeatStatus


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
    vacant: int
    occupied: int
    reserved: int
    out_of_service: int
    total: int
    utilization_percent: float
