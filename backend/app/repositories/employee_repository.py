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

    async def search_detailed(
        self,
        *,
        query: str | None = None,
        department_id: uuid.UUID | None = None,
        employment_status: str | None = None,
        project_id: uuid.UUID | None = None,
        floor_number: int | None = None,
        zone_id: uuid.UUID | None = None,
        seat_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[dict], int]:
        """Enriched version of search() that joins out to the employee's
        current project and seat, and supports the spec's full filter set
        (project/floor/zone/seat status), not just name/department/status.
        Returns dicts rather than ORM objects — see seat_repository.py
        list_all() for why (joined columns don't map onto the Employee
        model itself). Kept separate from search() because other code
        (the AI assistant, seat allocation flows) calls search() expecting
        real ORM Employee objects with further-queryable .id fields."""
        from app.models.department import Department
        from app.models.location import Floor, Zone
        from app.models.project import Project, ProjectAssignment
        from app.models.seat import Seat, SeatAllocation

        active_proj = (
            select(ProjectAssignment.employee_id, ProjectAssignment.project_id)
            .where(ProjectAssignment.end_date.is_(None))
            .subquery()
        )
        active_seat = (
            select(SeatAllocation.employee_id, SeatAllocation.seat_id)
            .where(SeatAllocation.release_date.is_(None))
            .subquery()
        )

        stmt = (
            select(
                Employee,
                Project.name.label("current_project_name"),
                Seat.seat_number.label("seat_number"),
                Seat.status.label("seat_status_value"),
            )
            .outerjoin(active_proj, active_proj.c.employee_id == Employee.id)
            .outerjoin(Project, Project.id == active_proj.c.project_id)
            .outerjoin(active_seat, active_seat.c.employee_id == Employee.id)
            .outerjoin(Seat, Seat.id == active_seat.c.seat_id)
        )

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
        if project_id:
            stmt = stmt.where(active_proj.c.project_id == project_id)
        if seat_status:
            stmt = stmt.where(Seat.status == seat_status)
        if floor_number is not None or zone_id is not None:
            stmt = stmt.join(Zone, Seat.zone_id == Zone.id).join(Floor, Zone.floor_id == Floor.id)
            if floor_number is not None:
                stmt = stmt.where(Floor.floor_number == floor_number)
            if zone_id is not None:
                stmt = stmt.where(Seat.zone_id == zone_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Employee.full_name).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).all()

        items = []
        for emp, proj_name, seat_number, seat_status_value in rows:
            items.append({
                "id": emp.id,
                "employee_code": emp.employee_code,
                "full_name": emp.full_name,
                "email": emp.email,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "manager_id": emp.manager_id,
                "employment_status": emp.employment_status,
                "date_of_joining": emp.date_of_joining,
                "location": emp.location,
                "role": emp.role,
                "is_active": emp.is_active,
                "created_at": emp.created_at,
                "updated_at": emp.updated_at,
                "current_project_name": proj_name,
                "seat_allocation_status": "Allocated" if seat_number else "Unallocated",
                "seat_number": seat_number,
            })
        return items, total

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

    async def count_without_active_seat(self) -> int:
        """Lightweight count version of get_without_active_seat, for dashboard cards."""
        from app.models.seat import SeatAllocation

        subq = select(SeatAllocation.employee_id).where(SeatAllocation.release_date.is_(None))
        stmt = select(func.count()).select_from(Employee).where(
            Employee.id.not_in(subq), Employee.is_active.is_(True)
        )
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
