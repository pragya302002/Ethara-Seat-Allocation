from fastapi import APIRouter

from app.api.v1.assistant import router as assistant_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.employees import router as employees_router
from app.api.v1.projects import router as projects_router
from app.api.v1.seats import router as seats_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(employees_router)
api_router.include_router(projects_router)
api_router.include_router(seats_router)
api_router.include_router(dashboard_router)
api_router.include_router(assistant_router)
