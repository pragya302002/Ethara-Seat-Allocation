"""
Import every model module here. Alembic's autogenerate compares
Base.metadata against the live DB — if a model isn't imported somewhere
that gets loaded before autogenerate runs, Alembic silently won't see it
and will generate a migration that DROPS its table. This file exists
specifically to prevent that class of bug.
"""
from app.database.session import Base  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.location import Building, Floor, Zone  # noqa: F401
from app.models.employee import Employee  # noqa: F401
from app.models.project import Project, ProjectAssignment  # noqa: F401
from app.models.seat import Seat, SeatAllocation  # noqa: F401

__all__ = [
    "Base",
    "Department",
    "Building",
    "Floor",
    "Zone",
    "Employee",
    "Project",
    "ProjectAssignment",
    "Seat",
    "SeatAllocation",
]
