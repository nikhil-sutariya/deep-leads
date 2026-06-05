import asyncio
from loguru import logger
from contextlib import asynccontextmanager
from app.core.database import AsyncSessionLocal, engine
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import get_settings
from app.services.follow_up_scheduler import start_follow_up_scheduler, stop_follow_up_scheduler
from sqlalchemy import text, select


settings = get_settings()

@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for database connection"""
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1").execution_options(timeout=10))
            logger.info("Database connection established successfully")
            break
        except Exception as e:
            logger.warning(f"DB connection attempt {attempt}/{retries} failed: {e}")
            if attempt == retries:
                raise
            await asyncio.sleep(3 * attempt)

    # ---- Seed default admin user (idempotent) ----
    try:
        default_email = getattr(settings, "default_admin_email", "admin@example.com").lower()
        default_password = getattr(settings, "default_admin_password", "Admin@1234")

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == default_email)
            )
            admin_user = result.scalars().first()

            if not admin_user:
                user = User(
                    email=default_email,
                    first_name="Admin",
                    last_name="User",
                    password=get_password_hash(default_password),
                )
                session.add(user)
                await session.commit()
                logger.info(f"Seeded default admin user: {default_email}")
            else:
                logger.info("Default admin user already exists — skipping seeding.")

    except Exception as e:
        logger.warning(f"Could not seed default user: {e}")

    start_follow_up_scheduler()

    yield

    stop_follow_up_scheduler()
    await engine.dispose()
    logger.info("Database connections closed")
