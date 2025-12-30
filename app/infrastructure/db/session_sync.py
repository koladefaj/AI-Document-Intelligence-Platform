from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.config import settings

engine = create_engine(settings.database_sync_url, echo=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db_sync():
    """ synchronous DB session"""
    return SessionLocal()