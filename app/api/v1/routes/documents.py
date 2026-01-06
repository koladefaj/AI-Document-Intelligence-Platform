import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from sqlalchemy import select
from uuid import UUID
from app.infrastructure.db.session import get_session
from app.infrastructure.auth.dependencies import get_current_user
from app.application.use_case.upload_document import handle_upload
from app.application.use_case.process_document import queue_processing
from app.domain.services.storage_interface import StorageInterface
from app.dependencies import get_storage_service
from app.core.security import validate_file_content
from app.core.limiter import limiter

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def upload_document(
        request: Request,
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session),
        user = Depends(get_current_user),
        storage: StorageInterface = Depends(get_storage_service)
):
    """
    Main upload endpoint. 
    Coordinates validation, storage, and background AI processing.
    """
    # 1. Security Check: Validate Magic Bytes & Size
    await validate_file_content(file)

    try:
        # 2. Application Logic: Save to DB and Physical Storage
        # Returning the tuple as requested for internal app use
        doc = await handle_upload(file, session, user, storage)

        # 3. Background Task: Dispatch to Celery/Gemini
        # We pass the doc.id (UUID) so the worker can fetch it from the DB
        task_info = queue_processing(str(doc.id))

        logger.info(f"User {user.email} uploaded document {doc.id}. Task {task_info['task_id']} started.")

        return {
            "message": "Upload Successful. Analysis is running in the background.",
            "document_id": str(doc.id),
            "task_id": task_info["task_id"],
            "status": "PROCESSING",
            "file_name": doc.file_name,
            "url": doc.url,
            "owner": user.email
        }

    except Exception as e:
        # Emergency rollback if something fails between DB and Storage
        await session.rollback()
        logger.error(f"Critical Upload Failure: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload could not be completed. Error: {type(e).__name__}"
        )
    

@router.get("/{document_id}")
async def get_document(
    document_id: UUID, 
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    """
    Retrieve a specific document's analysis and status.
    """
    # 1. Fetch document from DB
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()

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

    return {
        "id": str(doc.id),
        "file_name": doc.file_name,
        "status": doc.status,
        "raw_text_preview": doc.raw_text[:500] if doc.raw_text else None, # First 500 chars
        "analysis": doc.analysis, # This is your JSON results from the AI
        "created_at": doc.created_at
    }

@router.get("/")
async def list_my_documents(
    session: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    """
    List all documents belonging to the logged-in user.
    """
    result = await session.execute(
        select(Document).where(Document.owner_id == user.id)
    )
    documents = result.scalars().all()
    return documents