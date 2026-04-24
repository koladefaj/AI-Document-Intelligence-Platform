import pytest
from httpx import AsyncClient
from starlette import status
from unittest.mock import patch

@pytest.mark.asyncio
async def test_upload_document_success(client: AsyncClient):
    """Test that a logged-in user can upload a PDF."""
    # 1. Register and Login to get a token
    user_data = {"email": "uploader@example.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=user_data)
    login_res = await client.post("/api/v1/auth/login", json={"email": "uploader@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    file_content = b"%PDF-1.4 mock pdf content"
    files = {"file": ("test_doc.pdf", file_content, "application/pdf")}
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.v1.routes.documents.queue_processing") as mock_queue:

        mock_queue.return_value = {
            "task_id": "mock-task-123",
            "document_id": "some-uuid"
        }
        
        response = await client.post(
            "/api/v1/documents/upload", 
            headers=headers, 
            files=files
        )

    assert response.status_code == 201
    assert response.json()["task_id"] == "mock-task-123"

@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient):
    """Test that uploading without a token fails."""
    files = {"file": ("test.pdf", b"content", "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]