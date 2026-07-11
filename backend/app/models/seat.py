"""
Seat + SeatAllocation.

Same pattern as ProjectAssignment: an employee's current seat is derived
from the SeatAllocation row with release_date IS NULL, not a direct FK on
either Employee or Seat. This single history table serves four brief
requirements at once: Allocate, Release, Transfer (= release + allocate in
one transaction, same employee), and "View History" (just query all rows
for a seat or employee, ordered by allocation_date).

seat.status is a denormalized cache column (VACANT/OCCUPIED/RESERVED/
OUT_OF_SERVICE), updated by the service layer whenever an allocation event
is written. This is a deliberate denormalization: dashboard occupancy
queries ("vacant seats on Floor 3") run far more often than allocation
writes, so paying a small consistency-management cost in the service layer
buys a plain indexed WHERE status = 'vacant' instead of a correlated
subquery against seat_allocations on every dashboard load.
"""
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import SeatStatus, SeatType, AllocationEventType
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Seat(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("zone_id", "seat_number", name="uq_zone_seat_number"),
        Index("ix_seat_status", "status"),  # supports fast vacancy dashboard/search queries
    )

    seat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    row_label: Mapped[str | None] = mapped_column(String(10), nullable=True)  # see location.py docstring
    seat_type: Mapped[SeatType] = mapped_column(nullable=False, default=SeatType.STANDARD)
    status: Mapped[SeatStatus] = mapped_column(nullable=False, default=SeatStatus.VACANT)

    zone: Mapped["Zone"] = relationship(back_populates="seats")
    allocations: Mapped[list["SeatAllocation"]] = relationship(back_populates="seat")


class SeatAllocation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "seat_allocations"
    __table_args__ = (
        Index(
            "uq_seat_active_allocation",
            "seat_id",
            unique=True,
            postgresql_where="release_date IS NULL",
        ),
        Index(
            "uq_employee_active_seat",
            "employee_id",
            unique=True,
            postgresql_where="release_date IS NULL",
        ),
    )

    seat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[AllocationEventType] = mapped_column(nullable=False, default=AllocationEventType.ALLOCATE)
    allocation_date: Mapped[date] = mapped_column(Date, nullable=False)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # NULL = currently occupying this seat

    seat: Mapped["Seat"] = relationship(back_populates="allocations")
    employee: Mapped["Employee"] = relationship(back_populates="seat_allocations", foreign_keys=[employee_id])
