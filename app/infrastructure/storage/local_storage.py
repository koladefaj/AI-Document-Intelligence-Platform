import os
from app.domain.services.storage_interface import StorageInterface

LOCAL_UPLOAD_DIR = "app/files"

os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)

class LocalStorage(StorageInterface):
    def upload(self, file_id: str, file_bytes: bytes, content_type: str) -> str:
        file_path = os.path.join(LOCAL_UPLOAD_DIR, file_id)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        return f"/local-files/{file_id}"