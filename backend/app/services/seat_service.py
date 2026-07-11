"""
Seat allocation business logic.

Concurrency note: two admins could try to allocate the same vacant seat at
nearly the same moment. Rather than a hand-rolled "check then write" race
(SELECT is vacant -> INSERT), we let the database's partial unique index
(`uq_seat_active_allocation` from models/seat.py) be the source of truth
for "this seat already has an active allocation," and catch the resulting
IntegrityError here to turn it into a clean 409 response. This is more
robust than an application-level check under concurrent load, and it's
the same reason the DB constraint exists in the first place rather than
only being enforced in this service.
"""
from datetime import date as date_type
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AllocationEventType, SeatStatus
from app.models.seat import SeatAllocation
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.seat_repository import SeatRepository
from app.schemas.seat import SeatAllocationRequest, SeatReleaseRequest, SeatTransferRequest


class SeatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.seats = SeatRepository(db)
        self.employees = EmployeeRepository(db)

    async def allocate(self, payload: SeatAllocationRequest) -> SeatAllocation:
        seat = await self.seats.get_by_id(payload.seat_id)
        if seat is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Seat not found")
        if seat.status != SeatStatus.AVAILABLE:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Seat is currently {seat.status.value}, not vacant")

        employee = await self.employees.get_by_id(payload.employee_id)
        if employee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")

        existing = await self.seats.get_active_allocation_for_employee(payload.employee_id)
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Employee already has an active seat — use transfer instead of allocate",
            )

        allocation = SeatAllocation(
            seat_id=seat.id,
            employee_id=employee.id,
            event_type=AllocationEventType.ALLOCATE,
            allocation_date=payload.allocation_date or date_type.today(),
        )
        try:
            await self.seats.create_allocation(allocation)
            seat.status = SeatStatus.OCCUPIED
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Seat was allocated by another request just now")

        await self.db.refresh(allocation)
        return allocation

    async def release(self, payload: SeatReleaseRequest) -> SeatAllocation:
        active = await self.seats.get_active_allocation_for_seat(payload.seat_id)
        if active is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Seat has no active allocation to release")

        active.release_date = payload.release_date or date_type.today()
        seat = await self.seats.get_by_id(payload.seat_id)
        seat.status = SeatStatus.AVAILABLE
        await self.db.commit()
        await self.db.refresh(active)
        return active

    async def transfer(self, payload: SeatTransferRequest) -> SeatAllocation:
        """Release the employee's current seat (if any) and allocate the new
        one, as a single DB transaction — either both happen or neither
        does, so an employee can never end up seatless due to a
        half-completed transfer."""
        new_seat = await self.seats.get_by_id(payload.new_seat_id)
        if new_seat is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Target seat not found")
        if new_seat.status != SeatStatus.AVAILABLE:
            raise HTTPException(status.HTTP_409_CONFLICT, "Target seat is not vacant")

        transfer_date = payload.transfer_date or date_type.today()

        current = await self.seats.get_active_allocation_for_employee(payload.employee_id)
        if current is not None:
            current.release_date = transfer_date
            old_seat = await self.seats.get_by_id(current.seat_id)
            old_seat.status = SeatStatus.AVAILABLE

        new_allocation = SeatAllocation(
            seat_id=new_seat.id,
            employee_id=payload.employee_id,
            event_type=AllocationEventType.TRANSFER,
            allocation_date=transfer_date,
        )
        try:
            self.db.add(new_allocation)
            new_seat.status = SeatStatus.OCCUPIED
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Target seat was allocated by another request just now")

        await self.db.refresh(new_allocation)
        return new_allocation

    async def occupancy_summary(self) -> dict:
        return await self.seats.occupancy_summary()
