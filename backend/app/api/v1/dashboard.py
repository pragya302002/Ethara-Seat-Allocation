from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.schemas.dashboard import DashboardSummary, DepartmentCount, FloorUtilization, ProjectCount
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await DashboardService(db).summary()


@router.get("/project-utilization", response_model=list[ProjectCount])
async def project_utilization(
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await DashboardService(db).project_utilization()


@router.get("/floor-utilization", response_model=list[FloorUtilization])
async def floor_utilization(
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    return await DashboardService(db).floor_utilization()
