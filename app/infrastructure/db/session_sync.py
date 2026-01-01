import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.infrastructure.config import settings

# Initialize logger for database connection events
logger = logging.getLogger(__name__)

# --- 1. ENGINE CONFIGURATION ---
# Dev Note: We use the 'database_sync_url' (psycopg2) here, NOT the asyncpg one.
# 'pool_pre_ping=True' checks if the connection is alive before using it,
# which is vital in Docker if the Postgres container restarts.
engine = create_engine(
    settings.database_sync_url, 
    echo=False,  # Set to True only for heavy SQL debugging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# --- 2. SESSION FACTORY ---
# autoflush=False: Prevents SQL from being sent to the DB before you call commit()
# autocommit=False: Standard SQLAlchemy 2.0 practice
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False,
    expire_on_commit=False  # Keeps objects readable after commit()
)

def get_db_sync() -> Session:
    """
    Standard synchronous DB session provider for Celery workers.
    
    Usage in worker:
        db = get_db_sync()
        try:
            # logic
        finally:
            db.close()
    """
    logger.debug("Database: Creating new synchronous session for worker.")
    return SessionLocal()

# --- 3. CONTEXT MANAGER (Preferred for clean code) ---
from contextlib import contextmanager

@contextmanager
def db_session_scope():
    """
    Provide a transactional scope around a series of operations.
    Usage:
        with db_session_scope() as db:
            db.add(item)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database Scope Error: {e}")
        raise
    finally:
        session.close()