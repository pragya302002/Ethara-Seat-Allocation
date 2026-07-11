import uuid

from sqlalchemy import or_, select, func
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    model = Employee

    async def get_by_email(self, email: str) -> Employee | None:
        result = await self.db.execute(select(Employee).where(Employee.email == email))
        return result.scalar_one_or_none()

    async def get_by_code(self, employee_code: str) -> Employee | None:
        result = await self.db.execute(select(Employee).where(Employee.employee_code == employee_code))
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        query: str | None = None,
        department_id: uuid.UUID | None = None,
        employment_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Employee], int]:
        """Structured filtered search backing the /employees endpoint and
        the Global Search feature's non-NL path. Returns (rows, total_count)
        so the API layer can build pagination metadata without a second
        round trip."""
        stmt = select(Employee).options(selectinload(Employee.department))

        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Employee.full_name.ilike(like),
                    Employee.employee_code.ilike(like),
                    Employee.email.ilike(like),
                )
            )
        if department_id:
            stmt = stmt.where(Employee.department_id == department_id)
        if employment_status:
            stmt = stmt.where(Employee.employment_status == employment_status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Employee.full_name).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows), total

    async def department_counts(self) -> list[dict]:
        """Powers dashboard's 'Department-wise Allocation' chart."""
        from app.models.department import Department

        stmt = (
            select(Department.name, func.count(Employee.id))
            .join(Employee, Employee.department_id == Department.id, isouter=True)
            .where((Employee.is_active.is_(True)) | (Employee.id.is_(None)))
            .group_by(Department.name)
            .order_by(func.count(Employee.id).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [{"department": name, "count": count} for name, count in rows]

    async def new_joiners_count(self, days: int = 30) -> int:
        """Employees who joined within the last N days — dashboard 'New Joiners' card."""
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days)
        stmt = select(func.count()).select_from(Employee).where(Employee.date_of_joining >= cutoff)
        return (await self.db.execute(stmt)).scalar_one()

    async def total_active_count(self) -> int:
        stmt = select(func.count()).select_from(Employee).where(Employee.is_active.is_(True))
        return (await self.db.execute(stmt)).scalar_one()

    async def get_without_active_seat(self, page: int = 1, page_size: int = 25) -> tuple[list[Employee], int]:
        """Employees with no open (release_date IS NULL) SeatAllocation row —
        backs the 'New Joiner Allocation: view employees without seats' requirement."""
        from app.models.seat import SeatAllocation  # local import avoids a circular import at module load

        subq = select(SeatAllocation.employee_id).where(SeatAllocation.release_date.is_(None))
        stmt = select(Employee).where(Employee.id.not_in(subq), Employee.is_active.is_(True))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Employee.date_of_joining.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows), total
