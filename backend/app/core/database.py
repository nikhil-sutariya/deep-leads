"""
Async database connection and session management (no RLS/admin)
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger
from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
	"""Base class for SQLAlchemy models"""
	pass


# Single async engine (simple setup, suitable for this project)
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",   # Set to True for SQL query logging
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,                                 # reasonable default for t3.micro / dev
    max_overflow=20,                              # allow burst load
    connect_args={"timeout": 10},                 # fail fast if DB is unavailable
    # For production (2 vCPUs+), scale pool_size to ~20–30 and max_overflow to ~50.
)

AsyncSessionLocal = async_sessionmaker(
	engine,
	class_=AsyncSession,
	expire_on_commit=False,
	autoflush=False,
	autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
	"""
	FastAPI dependency to get an async DB session.
	Commits on success, rolls back on error, always closes.
	"""
	async with AsyncSessionLocal() as session:
		try:
			yield session
			await session.commit()
		except Exception:
			await session.rollback()
			raise
		finally:
			await session.close()

