import logging
import os
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Initialize logger for async database events
logger = logging.getLogger(__name__)

# --- DATABASE URL CONFIGURATION ---
# Get the base DATABASE_URL (sync version: postgresql://)
db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create async version for the application
async_db = db_url.replace('postgresql://', 'postgresql+asyncpg://')

# Keep sync version for Alembic (export this!)
# db_url remains as the sync version

# --- 1. ASYNC ENGINE CONFIGURATION ---
engine = create_async_engine(
    async_db,  # Use the async version
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Vital for Docker container stability
)

# --- 2. ASYNC SESSION FACTORY ---
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- 3. DEPENDENCY INJECTION ---
async def get_session() -> AsyncSession:
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