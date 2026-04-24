import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_return_health_check(client): # Using the 'client' fixture from conftest
    response = await client.get("/healthy")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "online"
    assert data["environment"] == "docker-container"
    assert "request_id" in data