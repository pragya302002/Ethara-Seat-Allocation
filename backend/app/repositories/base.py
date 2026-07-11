"""
Generic repository base class.

Repositories own ALL raw SQLAlchemy query construction. Services never
import `select`/`sqlalchemy` directly — they call repository methods. This
boundary is what lets us swap persistence details (e.g. add caching, change
an index strategy, even swap ORMs) without touching business logic, and
it's what makes services unit-testable with a mocked repository instead of
a real database.
"""
import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()
