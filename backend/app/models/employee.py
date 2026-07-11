"""
Employee model.

Design decision: Employee IS the authentication identity (email +
hashed_password + role live here) rather than a separate `users` table
joined 1:1 to `employees`. At this scale (~5k rows, single-tenant, no
non-employee system users like external API clients), splitting auth into
its own table adds a mandatory join on every authenticated request for no
real benefit. If this system later needs non-employee accounts (e.g. a
service account, or Ethara's clients as external stakeholders), that's the
trigger to split — noting that explicitly rather than doing it now.
"""
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import EmploymentStatus, UserRole
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Employee(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "employees"

    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.EMPLOYEE)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    designation: Mapped[str] = mapped_column(String(120), nullable=False)

    # Self-referential reporting manager. This is the field you clarified as
    # "Manage[r]" in the brief — the person responsible for this employee's
    # seating, distinct from a Project Manager (which is scoped to a Project).
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )

    employment_status: Mapped[EmploymentStatus] = mapped_column(nullable=False, default=EmploymentStatus.ACTIVE)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)  # city/office label, distinct from seat's building

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # --- Relationships ---
    department: Mapped["Department"] = relationship(back_populates="employees")
    manager: Mapped["Employee | None"] = relationship(remote_side="Employee.id", foreign_keys=[manager_id])

    # Current seat is derived from the latest open SeatAllocation row, not a
    # direct FK here — see seat_allocation.py docstring for why.
    seat_allocations: Mapped[list["SeatAllocation"]] = relationship(
        back_populates="employee", foreign_keys="SeatAllocation.employee_id"
    )
    project_assignments: Mapped[list["ProjectAssignment"]] = relationship(
        back_populates="employee", foreign_keys="ProjectAssignment.employee_id"
    )
