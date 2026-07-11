import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee, require_role
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.models.enums import UserRole
from app.repositories.seat_repository import SeatRepository
from app.schemas.seat import (
    OccupancySummary,
    SeatAllocationOut,
    SeatAllocationRequest,
    SeatOut,
    SeatReleaseRequest,
    SeatTransferRequest,
)
from app.services.seat_service import SeatService

router = APIRouter(prefix="/seats", tags=["Seats"])
WRITE_ROLES = require_role(UserRole.ADMIN, UserRole.HR)


@router.get("/vacant", response_model=list[SeatOut])
async def list_vacant_seats(
    zone_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await SeatRepository(db).list_vacant(zone_id=zone_id, floor_id=floor_id)


@router.get("/occupancy-summary", response_model=OccupancySummary)
async def occupancy_summary(
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await SeatService(db).occupancy_summary()


@router.get("/{seat_id}/history", response_model=list[SeatAllocationOut])
async def seat_history(
    seat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await SeatRepository(db).get_history_for_seat(seat_id)


@router.post("/allocate", response_model=SeatAllocationOut, status_code=status.HTTP_201_CREATED)
async def allocate_seat(
    payload: SeatAllocationRequest,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    return await SeatService(db).allocate(payload)


@router.post("/release", response_model=SeatAllocationOut)
async def release_seat(
    payload: SeatReleaseRequest,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    return await SeatService(db).release(payload)


@router.post("/transfer", response_model=SeatAllocationOut)
async def transfer_seat(
    payload: SeatTransferRequest,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    return await SeatService(db).transfer(payload)
