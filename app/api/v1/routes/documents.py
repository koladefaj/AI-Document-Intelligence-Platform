from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from app.infrastructure.db.session import get_session
from app.infrastructure.auth.dependencies import get_current_user
from app.application.use_case import upload_document, process_document
from app.domain.services.storage_interface import StorageInterface
from app.dependencies import get_storage_service


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

@router.post("/upload_document", status_code=status.HTTP_201_CREATED)
async def upload_document(
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session),
        user = Depends(get_current_user),
        storage: StorageInterface = Depends(get_storage_service)
):
    try:
        doc, url, local_path = await upload_document.handle_upload(file, session, user, storage)

        task = process_document.queue_processing(doc.id)

        return {
            "message": "Upload Successful",
            "document_id": str(doc.id),
            "task_id": task.id,
            "status": "PROCESSING",
            "url": url
        }


    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SERVER ERROR: {type(e).__name__}: {e}"
        )

