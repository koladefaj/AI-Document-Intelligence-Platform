import pytest
from httpx import AsyncClient
from starlette import status
from unittest.mock import patch

@pytest.mark.asyncio
async def test_document_access_security(client: AsyncClient):
    """Ensure User A cannot access User B's documents."""
    
    # 1. Setup User A
    user_a = {"email": "user_a@test.com", "password": "password"}
    await client.post("/api/v1/auth/register", json=user_a)
    login_a = await client.post("/api/v1/auth/login", json=user_a)
    token_a = login_a.json()["access_token"]
    
    files = {"file": ("secret.pdf", b"%PDF-1.4\n content", "application/pdf")}

    # 2. Mock the dispatch at the ROUTE level to stop Redis connection attempts
    with patch("app.api.v1.routes.documents.queue_processing") as mock_queue:

        mock_queue.return_value = {"task_id": "mock-task-123"}
        
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token_a}"},
            files=files
        )

    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # 3. Setup User B
    user_b = {"email": "user_b@test.com", "password": "password"}
    await client.post("/api/v1/auth/register", json=user_b)
    login_b = await client.post("/api/v1/auth/login", json=user_b)
    token_b = login_b.json()["access_token"]

    # 4. User B tries to access User A's document
    response = await client.get(
        f"/api/v1/documents/{doc_id}", 
        headers={"Authorization": f"Bearer {token_b}"}
    )

    # 5. Assert Protection (404 or 403)
    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]