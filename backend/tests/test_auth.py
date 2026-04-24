import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_register_user_success(client):
    """Test that a user can register successfully."""
    payload = {
        "email": "testuser@example.com",
        "password": "strongpassword123",
    }
    
    response = await client.post("/api/v1/auth/register", json=payload)

    if response.status_code != 201:
        print(f"Error detail: {response.json()}")
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == payload["email"]
    assert "id" in response.json()

@pytest.mark.asyncio
async def test_login_success(client):
    """Test that the registered user can log in and get a JWT."""
    # 1. First, register the user
    user_data = {"email": "login@example.com", "password": "password"}
    await client.post("/api/v1/auth/register", json=user_data)
    
    # 2. Try to login
    login_data = {"email": "login@example.com", "password": "password"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"