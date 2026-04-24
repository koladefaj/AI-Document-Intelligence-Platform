import logging
from app.infrastructure.db.session import db_url
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Initialize logger for database connection events
logger = logging.getLogger(__name__)

# --- 1. ENGINE CONFIGURATION ---
# Use the 'database_sync_url' (psycopg2) here, NOT the asyncpg one.

engine = create_engine(
    db_url, 
    echo=False,  # Set to True only for heavy SQL debugging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# --- 2. SESSION FACTORY ---
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False,
    expire_on_commit=False  # Keeps objects readable after commit()
)

def get_db_sync() -> Session:
    """
    Standard synchronous DB session provider for Celery workers.
    """
    logger.debug("Database: Creating new synchronous session for worker.")
    return SessionLocal()

# --- 3. CONTEXT MANAGER (Preferred for clean code) ---

@contextmanager
def db_session_scope():
    """
    Provide a transactional scope around a series of operations.
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