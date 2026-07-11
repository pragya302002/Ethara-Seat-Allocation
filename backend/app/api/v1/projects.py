import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee, require_role
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.models.enums import UserRole
from app.models.project import Project as ProjectModel
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import (
    ProjectAssignmentOut,
    ProjectAssignRequest,
    ProjectCreate,
    ProjectOut,
    ProjectPage,
    ProjectUpdate,
)
from app.services.project_service import ProjectAssignmentService

router = APIRouter(prefix="/projects", tags=["Projects"])
WRITE_ROLES = require_role(UserRole.ADMIN, UserRole.HR)


@router.get("", response_model=ProjectPage)
async def list_projects(
    q: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    repo = ProjectRepository(db)
    rows, total = await repo.search(query=q, is_active=is_active, page=page, page_size=page_size)
    return ProjectPage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: EmployeeModel = Depends(get_current_employee)
):
    project = await ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, db: AsyncSession = Depends(get_db), _: EmployeeModel = Depends(WRITE_ROLES)
):
    repo = ProjectRepository(db)
    if await repo.get_by_code(payload.code) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Project code already exists")
    project = await repo.create(ProjectModel(**payload.model_dump()))
    await repo.commit()
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await repo.commit()
    await db.refresh(project)
    return project


@router.post("/{project_id}/assign", response_model=ProjectAssignmentOut, status_code=status.HTTP_201_CREATED)
async def assign_employee_to_project(
    project_id: uuid.UUID,
    payload: ProjectAssignRequest,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(WRITE_ROLES),
):
    return await ProjectAssignmentService(db).assign(project_id, payload)


@router.post("/unassign/{employee_id}", response_model=ProjectAssignmentOut)
async def remove_employee_from_project(
    employee_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: EmployeeModel = Depends(WRITE_ROLES)
):
    return await ProjectAssignmentService(db).remove(employee_id)
