"""
Idempotent database initializer.

Creates any missing tables defined by the SQLAlchemy models. Used by the
docker-compose `app` service on startup so a fresh Postgres volume gets a
working schema immediately.

For controlled schema evolution against an existing database, prefer
`alembic upgrade head` instead — this script intentionally does NOT run
alembic migrations.
"""
import asyncio

from loguru import logger

from app.core.database import Base, engine

# Import models so they register themselves with Base.metadata
from app.models.lead import LeadDB, CampaignDB, CampaignEmailDB  # noqa: F401
from app.models.user import User, Notification  # noqa: F401


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema is up to date (create_all)")


if __name__ == "__main__":
    asyncio.run(init_db())
