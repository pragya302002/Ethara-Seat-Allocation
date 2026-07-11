import uuid

from sqlalchemy import select, func, or_

from app.models.project import Project, ProjectAssignment
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_by_code(self, code: str) -> Project | None:
        result = await self.db.execute(select(Project).where(Project.code == code))
        return result.scalar_one_or_none()

    async def search(
        self, *, query: str | None = None, is_active: bool | None = None, page: int = 1, page_size: int = 25
    ) -> tuple[list[Project], int]:
        stmt = select(Project)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(or_(Project.name.ilike(like), Project.code.ilike(like), Project.client.ilike(like)))
        if is_active is not None:
            stmt = stmt.where(Project.is_active == is_active)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Project.name).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows), total

    async def get_active_assignment_for_employee(self, employee_id: uuid.UUID) -> ProjectAssignment | None:
        stmt = select(ProjectAssignment).where(
            ProjectAssignment.employee_id == employee_id, ProjectAssignment.end_date.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_assignment(self, assignment: ProjectAssignment) -> ProjectAssignment:
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def employees_by_client(self, client_query: str) -> list[str]:
        """Backs 'List employees working for Client ABC' style AI Assistant queries."""
        from app.models.employee import Employee

        stmt = (
            select(Employee.full_name, Project.name)
            .join(ProjectAssignment, ProjectAssignment.project_id == Project.id)
            .join(Employee, Employee.id == ProjectAssignment.employee_id)
            .where(Project.client.ilike(f"%{client_query}%"), ProjectAssignment.end_date.is_(None))
        )
        rows = (await self.db.execute(stmt)).all()
        return [f"{name} ({project})" for name, project in rows]

    async def get_employees_for_project(self, project_id) -> list:
        """Backs GET /projects/{id}/employees — active assignments only."""
        from app.models.employee import Employee

        stmt = (
            select(Employee)
            .join(ProjectAssignment, ProjectAssignment.employee_id == Employee.id)
            .where(ProjectAssignment.project_id == project_id, ProjectAssignment.end_date.is_(None))
            .order_by(Employee.full_name)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def project_headcounts(self) -> list[dict]:
        """Powers dashboard's 'Project-wise Allocation' chart."""
        stmt = (
            select(Project.name, func.count(ProjectAssignment.id))
            .join(ProjectAssignment, ProjectAssignment.project_id == Project.id, isouter=True)
            .where(ProjectAssignment.end_date.is_(None))
            .group_by(Project.name)
            .order_by(func.count(ProjectAssignment.id).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [{"project": name, "count": count} for name, count in rows]
