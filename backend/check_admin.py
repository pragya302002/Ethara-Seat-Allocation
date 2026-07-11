import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.employee import Employee
from app.models.enums import UserRole

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Employee.email, Employee.full_name).where(Employee.role == UserRole.ADMIN).limit(1))
        row = result.first()
        print('Admin email:', row[0])
        print('Admin name:', row[1])

asyncio.run(main())
