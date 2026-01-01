import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.models import Document, User
from app.domain.services.storage_interface import StorageInterface

# Initialize logger
logger = logging.getLogger(__name__)

async def handle_upload(file, session: AsyncSession, user: User, storage: StorageInterface):
    """
    Coordinates the document upload workflow.
    
    Workflow:
    1. Sanitize the filename for safe storage.
    2. Create a 'PENDING' record in Postgres to generate a UUID.
    3. Stream file bytes to the Storage Provider (MinIO or Local) using that UUID.
    4. Update the DB record with the final storage path and commit.
    """
    
    # 1. Filename Sanitization
    # We replace spaces with underscores to prevent URL encoding issues later.
    clean_filename = os.path.basename(file.filename).replace(" ", "_")

    # 2. Initial Database Entry
    # We use "TEMP" placeholders because we don't know the final path until 
    # the storage provider finishes its work.
    doc = Document(
        file_name=clean_filename,
        content=file.content_type,
        owner_id=user.id,
        status="PENDING",
        url="TEMP",
        local_path="TEMP",
        raw_text="",
        analysis={} # Using empty dict as we updated the model to JSON
    )
    
    session.add(doc)
    
    # --- CRITICAL STEP: Flush ---
    # This communicates with Postgres to get the auto-generated UUID (doc.id)
    # but does NOT end the transaction. If storage fails, we can still rollback.
    await session.flush() 

    # 3. Preparation for Storage
    storage_file_id = str(doc.id)
    
    try:
        # Reset file cursor to start before reading
        await file.seek(0)
        file_bytes = await file.read()

        # 4. Storage Provider Handoff
        # 'final_path' will be the /app/storage/... path or the MinIO URL
        logger.info(f"Storage: Uploading document {storage_file_id} ({clean_filename})")
        final_path = await storage.upload(
            file_id=storage_file_id, 
            file_name=clean_filename, 
            file_bytes=file_bytes, 
            content_type=file.content_type
        )

        # 5. Metadata Finalization
        doc.local_path = final_path
        doc.url = f"/api/v1/files/{storage_file_id}" 
        
        # 6. Atomic Commit
        # Only now is the user's data officially saved to the DB.
        await session.commit()
        await session.refresh(doc)
        
        logger.info(f"Upload Complete: Document {doc.id} is ready for processing.")
        return doc
        
    except Exception as e:
        logger.error(f"Upload Handoff Failed: {str(e)}")
        await session.rollback()
        raise