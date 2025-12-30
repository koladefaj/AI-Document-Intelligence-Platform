import uuid, os
from fastapi import Depends
from app.infrastructure.db.models import Document
from app.domain.services.storage_interface import StorageInterface
from app.dependencies import get_storage_service



UPLOAD_DIR = "app/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def handle_upload(file, session, user, storage: StorageInterface = Depends(get_storage_service)):

    file_id = f"{uuid.uuid4()}-{file.filename}"
    local_path = os.path.join(UPLOAD_DIR, file_id)

    with open(local_path, "wb") as f:
        f.write(await file.read())

    # Upload to S3 / MinIO
    with open(local_path, "rb") as f:
        file_bytes = f.read()


    url = storage.upload(file_id, file.filename, file_bytes, file.content_type)

    # Save metadata in database
    doc = Document(
        file_name=file.filename,
        content = file.content_type,
        url = url,
        local_path = local_path,
        owner_id=user.id,
        status="PENDING"
    )
    session.add(doc)
    await session.commit()
    return doc, url, local_path
