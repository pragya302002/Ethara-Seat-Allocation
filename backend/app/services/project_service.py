from datetime import date as date_type

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectAssignment
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectAssignRequest


class ProjectAssignmentService:
    """Mirrors SeatService's pattern: DB partial-unique-index is the
    concurrency source of truth, service catches IntegrityError -> 409."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.projects = ProjectRepository(db)
        self.employees = EmployeeRepository(db)

    async def assign(self, project_id, payload: ProjectAssignRequest) -> ProjectAssignment:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        employee = await self.employees.get_by_id(payload.employee_id)
        if employee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")

        existing = await self.projects.get_active_assignment_for_employee(payload.employee_id)
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Employee already has an active project assignment — remove it first",
            )

        assignment = ProjectAssignment(
            employee_id=payload.employee_id,
            project_id=project_id,
            start_date=payload.start_date or date_type.today(),
            end_date=None,
        )
        try:
            await self.projects.create_assignment(assignment)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Assignment conflict — try again")

        await self.db.refresh(assignment)
        return assignment

    async def remove(self, employee_id) -> ProjectAssignment:
        active = await self.projects.get_active_assignment_for_employee(employee_id)
        if active is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Employee has no active project assignment")
        active.end_date = date_type.today()
        await self.db.commit()
        await self.db.refresh(active)
        return active
