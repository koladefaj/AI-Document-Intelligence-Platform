# tests/test_infra.py
import pytest
from httpx import AsyncClient
from sqlalchemy import text

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Verify that the FastAPI app is reachable via the test client."""
    response = await client.get("/docs") 
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_db_is_sqlite(db_session):
    """Verify that the database used in tests is actually SQLite (In-Memory)."""
    # This raw SQL query checks the database dialect
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    
    # Check if we are actually using SQLite
    bind = db_session.get_bind()
    assert "sqlite" in str(bind.url)