import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee, require_role
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.models.enums import SeatStatus, UserRole
from app.models.seat import Seat as SeatModel
from app.repositories.seat_repository import SeatRepository
from app.schemas.seat import (
    OccupancySummary,
    SeatAllocationOut,
    SeatAllocationRequest,
    SeatCreate,
    SeatOut,
    SeatPage,
    SeatReleaseRequest,
    SeatSuggestionOut,
    SeatTransferRequest,
)
from app.services.seat_service import SeatService

router = APIRouter(prefix="/seats", tags=["Seats"])
WRITE_ROLES = require_role(UserRole.ADMIN, UserRole.HR)


@router.get("", response_model=SeatPage)
async def list_seats(
    floor_number: int | None = Query(None, description="Filter by floor number"),
    zone_id: uuid.UUID | None = Query(None, description="Filter by zone"),
    status_filter: SeatStatus | None = Query(None, alias="status", description="Filter by seat status"),
    project_id: uuid.UUID | None = Query(None, description="Filter by the project currently occupying the seat"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    """General seat listing/search — returns each seat's floor, zone, bay,
    status, and (if occupied) the allocated employee and project."""
    repo = SeatRepository(db)
    rows, total = await repo.list_all(
        floor_number=floor_number,
        zone_id=zone_id,
        status=status_filter,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return SeatPage(items=rows, total=total, page=page, page_size=page_size)


@router.post("", response_model=SeatOut, status_code=status.HTTP_201_CREATED)
async def create_seat(
    payload: SeatCreate,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    repo = SeatRepository(db)
    seat = await repo.create_seat(SeatModel(**payload.model_dump()))
    await repo.commit()
    return seat


@router.get("/available", response_model=list[SeatOut])
async def list_available_seats(
    zone_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    """Matches the spec's exact endpoint name. Same underlying data as
    /seats/vacant (kept below for backward compatibility with the frontend
    already built against it)."""
    return await SeatRepository(db).list_vacant(zone_id=zone_id, floor_id=floor_id)


@router.get("/vacant", response_model=list[SeatOut])
async def list_vacant_seats(
    zone_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await SeatRepository(db).list_vacant(zone_id=zone_id, floor_id=floor_id)


@router.get("/suggest", response_model=SeatSuggestionOut)
async def suggest_seats(
    employee_id: uuid.UUID = Query(..., description="Employee to suggest seats for, typically a new joiner"),
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    """New Joiner Allocation: suggests available seats near the employee's
    project teammates, falling back to any available seats if none are
    nearby. See SeatRepository.suggest_seats_for_employee for the logic."""
    seats, basis = await SeatRepository(db).suggest_seats_for_employee(employee_id)
    return SeatSuggestionOut(suggested_seats=seats, suggestion_basis=basis)


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
