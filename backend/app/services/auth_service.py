from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.auth import LoginRequest, TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = EmployeeRepository(db)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        employee = await self.repo.get_by_email(payload.email)

        # Deliberately identical error for "no such email" and "wrong
        # password" — distinguishing them lets an attacker enumerate valid
        # employee emails via the login endpoint.
        invalid_credentials = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
        if employee is None or not verify_password(payload.password, employee.hashed_password):
            raise invalid_credentials
        if not employee.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

        token = create_access_token(subject=str(employee.id), role=employee.role.value)
        return TokenResponse(
            access_token=token,
            role=employee.role.value,
            employee_id=str(employee.id),
            full_name=employee.full_name,
        )
