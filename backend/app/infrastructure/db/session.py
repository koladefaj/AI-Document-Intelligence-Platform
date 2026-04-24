import logging
import os
from app.infrastructure.config import settings
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Initialize logger for async database events
logger = logging.getLogger(__name__)

# --- DATABASE URL CONFIGURATION ---
# Get URLs from settings
sync_url = settings.database_sync_url or settings.database_url
async_url = settings.database_url

if not sync_url or not async_url:
    raise ValueError("DATABASE_URL is not set in settings or environment")

# Ensure sync_url DOES NOT have asyncpg
if "+asyncpg" in sync_url:
    sync_url = sync_url.replace("+asyncpg", "")

# Ensure async_url DOES have asyncpg
if "+asyncpg" not in async_url:
    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

# Export for sync sessions
db_url = sync_url
async_db = async_url


# --- 1. ASYNC ENGINE CONFIGURATION ---
engine = create_async_engine(
    async_db,  # Use the async version
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
)

# --- 2. ASYNC SESSION FACTORY ---
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- 3. DEPENDENCY INJECTION ---
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency that provides an asynchronous database session.
    
    Workflow:
    1. Opens a connection from the pool.
    2. Yields the session to the path operation function.
    3. Automatically closes the session when the request is finished.
    """
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Database: New async session yielded for API request.")
            yield session
        except Exception as e:
            logger.error(f"Database: Async session error: {e}")
            await session.rollback()
            raise
        finally:
            # Closing the session returns the connection to the engine pool
            await session.close()