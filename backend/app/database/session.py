"""
Async database engine and session factory.

We use SQLAlchemy 2.0's async engine throughout (async Postgres driver) so
the whole request path — API -> service -> repository -> DB — stays
non-blocking. FastAPI is async-native; a sync DB driver here would
silently bottleneck concurrency under load.

Windows note: psycopg's async mode is incompatible with Windows' default
ProactorEventLoop and raises `InterfaceError` without this policy set —
see docs/DEBUGGING.md for the full explanation. This is a no-op on
Linux/Mac, so it's safe to leave in unconditionally rather than special-
casing the import per platform.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # avoids stale-connection errors after DB idles (common on free-tier hosts)
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
