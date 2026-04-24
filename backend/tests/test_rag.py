import pytest
from unittest.mock import patch
from uuid import uuid4

@pytest.fixture
async def setup_rag_test(client, db_session):
    from app.infrastructure.db.models import Document, User
    from app.infrastructure.auth.password import hash_password
    
    # 1. Create a test user
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"user_{uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # 2. Get auth headers
    login_res = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Create a test document
    doc = Document(
        id=uuid4(),
        file_name="test.pdf",
        url="http://test.com/test.pdf",
        local_path="/tmp/test.pdf", # Added missing field
        owner_id=user.id,
        status="PROCESSING",
        analysis={},
        raw_text="Some raw text content"
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    
    return {"headers": headers, "document": doc, "user": user}

@pytest.mark.asyncio
async def test_query_document_not_found(client, setup_rag_test):
    """Test querying a document that doesn't exist."""
    document_id = str(uuid4())
    response = await client.post(
        f"/api/v1/documents/{document_id}/query",
        headers=setup_rag_test["headers"],
        json={"query": "What is this document about?"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"

@pytest.mark.asyncio
@patch("app.infrastructure.processing.processor_service.DocumentProcessor.query_document")
async def test_query_document_success(mock_query, client, setup_rag_test):
    """Test successful document query."""
    # Setup mock response
    mock_query.return_value = {
        "answer": "This is a test answer.",
        "sources": [
            {
                "text": "Source text chunk",
                "score": 0.95,
                "metadata": {"page": 1}
            }
        ]
    }
    
    doc = setup_rag_test["document"]
    headers = setup_rag_test["headers"]
    
    # Mock document status to COMPLETED
    with patch("app.api.v1.routes.documents.DocumentRepository.get_by_id") as mock_get:
        doc.status = "COMPLETED"
        mock_get.return_value = doc
        
        response = await client.post(
            f"/api/v1/documents/{doc.id}/query",
            headers=headers,
            json={"query": "Who is the author?"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a test answer."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["text"] == "Source text chunk"

@pytest.mark.asyncio
async def test_query_document_not_ready(client, setup_rag_test):
    """Test querying a document that is still processing."""
    doc = setup_rag_test["document"]
    headers = setup_rag_test["headers"]
    
    # Mock document status to PROCESSING
    with patch("app.api.v1.routes.documents.DocumentRepository.get_by_id") as mock_get:
        doc.status = "PROCESSING"
        mock_get.return_value = doc
        
        response = await client.post(
            f"/api/v1/documents/{doc.id}/query",
            headers=headers,
            json={"query": "Is it ready?"}
        )
        
    assert response.status_code == 400
    assert "not ready" in response.json()["detail"]
