"""
Project + ProjectAssignment.

An employee's "current project" is derived by querying ProjectAssignment
for the row with end_date IS NULL, rather than storing a project_id
directly on Employee. This is what makes assignment *history* possible
(the brief's dashboard wants "recent allocations," and a realistic org
tracks who worked on what project over time) without a separate audit
table bolted on later. A partial unique index enforces "zero or one ACTIVE
project per employee" at the database level, not just in application code.
"""
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Project(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    client: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    team_size_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    manager: Mapped["Employee | None"] = relationship(foreign_keys=[manager_id])
    assignments: Mapped[list["ProjectAssignment"]] = relationship(back_populates="project")


class ProjectAssignment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "project_assignments"
    __table_args__ = (
        # Enforces "at most one ACTIVE assignment per employee" at the DB
        # level. Postgres partial unique index — only applies where
        # end_date IS NULL, so historical (ended) rows don't collide.
        Index(
            "uq_employee_active_assignment",
            "employee_id",
            unique=True,
            postgresql_where="end_date IS NULL",
        ),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # NULL = currently active assignment

    employee: Mapped["Employee"] = relationship(back_populates="project_assignments", foreign_keys=[employee_id])
    project: Mapped["Project"] = relationship(back_populates="assignments")
