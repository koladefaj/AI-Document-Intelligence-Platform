import logging
import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from uuid import UUID
from app.api.v1.schemas import DocumentAnalysisResponse, DocumentUploadResponse, QueryRequest, QueryResponse
from app.infrastructure.db.session import get_session
from app.infrastructure.auth.dependencies import get_current_user
from app.application.use_case.upload_document import handle_upload
from app.application.use_case.process_document import queue_processing
from app.domain.services.storage_interface import StorageInterface
from app.dependencies import get_storage_service, get_rag_service
from app.core.security import validate_file_content
from app.domain.exceptions import AuthenticationFailed
from app.core.limiter import limiter
from app.infrastructure.db.repository import DocumentRepository

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=DocumentUploadResponse)
@limiter.limit("5/minute")
async def upload_document(
        request: Request,
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session),
        user = Depends(get_current_user),
        storage: StorageInterface = Depends(get_storage_service)
) -> DocumentUploadResponse:
    """
    Main upload endpoint. 
    Coordinates validation, storage, and background AI processing.
    """
    # 1. Security Check: Validate Magic Bytes & Size
    await validate_file_content(file)

    try:
        # 2. Application Logic: Save to DB and Physical Storage
        doc = await handle_upload(file, session, user, storage)

        # 3. Background Task: Dispatch to Celery/Gemini
        task_info = queue_processing(str(doc.id))

        logger.info(f"User {user.email} uploaded document {doc.id}. Task {task_info['task_id']} started.")

        return DocumentUploadResponse(
            message="Upload Successful. Analysis is running in the background.",
            document_id=str(doc.id),
            task_id=task_info["task_id"],
            status="PROCESSING",
            file_name=doc.file_name,
            url=doc.url,
            owner= user.email
        )

    except AuthenticationFailed as e:
        # Pass through the specific duplicate/auth error with a 409 Conflict
        logger.warning(f"Upload Guardrail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        # Rollback is handled inside handle_upload for DB/Storage consistency
        logger.error(f"Upload Route Failure: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload could not be completed. Please try again."
        )
    

@router.get("/{document_id}", response_model=DocumentAnalysisResponse)
async def get_document(
    document_id: UUID, 
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
) -> DocumentAnalysisResponse:
    """
    Retrieve a specific document's analysis and status.
    """
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)

    # 2. Check if exists
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Document not found"
        )

    # 3. Security: Ensure the user requesting it owns it
    if doc.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to view this document"
        )

    return DocumentAnalysisResponse(
        id=str(doc.id),
        file_name=doc.file_name,
        url=doc.url,
        owner=user.email,
        status=doc.status,
        analysis_results=doc.analysis,
        created_at=doc.created_at
    ) 

@router.get("/")
async def list_my_documents(
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    """
    List all documents belonging to the logged-in user.
    """
    repo = DocumentRepository(session)
    return await repo.list_by_owner(user.id)


@router.post("/{document_id}/query", response_model=QueryResponse)
async def query_document(
    document_id: UUID,
    query_data: QueryRequest,
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
    rag_service = Depends(get_rag_service)
) -> QueryResponse:
    """
    Query a specific document using RAG.
    """
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Document not found"
        )

    if doc.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to query this document"
        )

    if doc.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is not ready for querying. Current status: " + doc.status
        )

    try:
        from app.infrastructure.db.session_sync import SessionLocal
        
        # Offload sync RAG logic to a thread to keep the API responsive
        def _sync_query():
            with SessionLocal() as sync_session:
                return rag_service.query(sync_session, str(document_id), query_data.query)
        
        result = await asyncio.to_thread(_sync_query)
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Query Error for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while querying the document."
        )


@router.get("/{document_id}/chat")
async def get_chat_history(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    """
    Retrieve persistent chat history for a document.
    """
    repo = DocumentRepository(session)
    history = await repo.get_chat_history(document_id, user.id)
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in history]

@router.get("/{document_id}/stream")
async def stream_query_document(
    document_id: UUID,
    query: str,
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
    rag_service = Depends(get_rag_service)
):
    """
    Stream a RAG query response token by token, with persistent history.
    """
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)

    if not doc or doc.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Document not ready")

    # 1. Fetch History for Context
    history_models = await repo.get_chat_history(document_id, user.id)
    # Take last 10 messages for context
    context_history = [{"role": m.role, "content": m.content} for m in history_models[-10:]]

    # 2. Save User Message
    await repo.add_chat_message(document_id, user.id, "user", query)

    async def event_generator():
        # We'll accumulate the response to save it at the end
        full_response = []

        # Run the blocking generator in a thread but yield chunks as they come
        def _stream_wrapper():
            # This runs in a separate thread
            from app.infrastructure.db.session_sync import SessionLocal
            with SessionLocal() as sync_session:
                return rag_service.stream_query(sync_session, str(document_id), query, context_history)

        # Use asyncio.to_thread to run the generator and yield from it
        # Actually, for a generator, we need a different approach to keep it streaming
        loop = asyncio.get_event_loop()
        generator = await loop.run_in_executor(None, _stream_wrapper)

        while True:
            # Get next chunk in a thread-safe way
            chunk = await loop.run_in_executor(None, next, generator, None)
            if chunk is None:
                break
            
            full_response.append(chunk)
            yield chunk

        # 3. Save AI Message once complete
        complete_text = "".join(full_response)
        def _save_ai_msg():
            from app.infrastructure.db.session_sync import SessionLocal
            with SessionLocal() as sync_session:
                from app.infrastructure.db.models import ChatMessage
                msg = ChatMessage(document_id=document_id, user_id=user.id, role="assistant", content=complete_text)
                sync_session.add(msg)
                sync_session.commit()
        
        await asyncio.to_thread(_save_ai_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
    storage: StorageInterface = Depends(get_storage_service)
):
    """
    Delete a document and its associated storage/embeddings.
    """
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Document not found"
        )

    if doc.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to delete this document"
        )

    try:
        # 1. Delete from Physical Storage (R2/Local/MinIO)
        await storage.delete(str(doc.id))

        # 2. Delete from DB (Embeddings will cascade delete)
        await repo.delete(doc)
        
        logger.info(f"User {user.email} deleted document {document_id}")
        return None
    except Exception as e:
        logger.error(f"Delete Error for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fully delete document. Storage may be out of sync."
        )