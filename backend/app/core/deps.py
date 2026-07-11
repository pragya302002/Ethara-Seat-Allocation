"""
Auth dependencies for FastAPI routes.

require_role(...) returns a dependency, so routes declare their own
authorization inline (e.g. `Depends(require_role(UserRole.ADMIN, UserRole.HR))`)
instead of duplicating if-checks in every endpoint body.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.employee import Employee
from app.models.enums import UserRole
from app.repositories.employee_repository import EmployeeRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_employee(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise CREDENTIALS_EXCEPTION

    try:
        employee_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise CREDENTIALS_EXCEPTION

    repo = EmployeeRepository(db)
    employee = await repo.get_by_id(employee_id)
    if employee is None or not employee.is_active:
        raise CREDENTIALS_EXCEPTION
    return employee


def require_role(*allowed_roles: UserRole):
    async def _check(current: Employee = Depends(get_current_employee)) -> Employee:
        if current.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in allowed_roles]}",
            )
        return current

    return _check
