"""
Dashboard service.

Note on concurrency: it's tempting to fire these 7 aggregate queries
concurrently with asyncio.gather to cut round-trip latency to Railway's
Postgres. That was tried here and deliberately reverted — a single
SQLAlchemy AsyncSession wraps one underlying DB connection and cannot run
concurrent operations on it; doing so raises InvalidRequestError at
runtime (confirmed while building this). Real concurrency would require a
separate session per query, which trades query-count round trips for
connection-pool pressure — not a clearly better trade for a single
dashboard load. Sequential awaits on one session is the correct choice
here, not just the simple one.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.employee_repository import EmployeeRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.seat_repository import SeatRepository


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.employees = EmployeeRepository(db)
        self.projects = ProjectRepository(db)
        self.seats = SeatRepository(db)

    async def summary(self) -> dict:
        total_employees = await self.employees.total_active_count()
        new_joiners = await self.employees.new_joiners_count(days=30)
        occupancy = await self.seats.occupancy_summary()
        dept_counts = await self.employees.department_counts()
        project_counts = await self.projects.project_headcounts()
        floor_util = await self.seats.floor_utilization()
        recent_alloc = await self.seats.recent_allocations(limit=10)
        recent_release = await self.seats.recent_releases(limit=10)

        return {
            "total_employees": total_employees,
            "new_joiners_last_30_days": new_joiners,
            "occupancy": occupancy,
            "department_wise": dept_counts,
            "project_wise": project_counts,
            "floor_utilization": floor_util,
            "recent_allocations": recent_alloc,
            "recent_releases": recent_release,
        }
