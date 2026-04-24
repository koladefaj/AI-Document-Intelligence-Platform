import logging
from pathlib import Path
from app.domain.services.storage_interface import StorageInterface

# Initialize logger for storage operations
logger = logging.getLogger(__name__)

# --- DIRECTORY CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOCAL_UPLOAD_DIR = BASE_DIR / "app" / "files"


try:
    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Storage Initialized: Local uploads directory is {LOCAL_UPLOAD_DIR}")
except Exception as e:
    logger.critical(f"STORAGE FAILURE: Could not create upload directory {LOCAL_UPLOAD_DIR}: {e}")

class LocalStorage(StorageInterface):
    """
    Handles file persistence on the local container filesystem.
    Used as the default storage provider if MinIO is disabled.
    """

    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        """
        Saves raw bytes to the disk.
        
        Args:
            file_id: Unique identifier (usually the Document UUID).
            file_name: Original name of the uploaded file.
            file_bytes: The actual file data.
            content_type: MIME type (e.g., 'application/pdf').
            
        Returns:
            The absolute string path where the file was saved.
        """
        file_path = LOCAL_UPLOAD_DIR / file_id
        
        try:
            # Using 'wb' for Write Binary mode
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            
            logger.info(f"File stored successfully: {file_id} at {file_path}")
            return str(file_path)
        except PermissionError:
            logger.error(f"PERMISSION DENIED: Cannot write to {file_path}. Check Docker volume permissions.")
            raise
        except Exception as e:
            logger.error(f"UPLOAD FAILED: {str(e)}")
            raise

    async def get_file_path(self, file_id: str) -> str:
        """
        Resolves the local path for a given file ID.
        
        """
        file_path = LOCAL_UPLOAD_DIR / file_id
        
        if not file_path.exists():
            logger.warning(f"File lookup failed: {file_id} not found at {file_path}")
            
        return str(file_path)

    async def delete(self, file_id: str) -> bool:
        """Deletes the file from the local filesystem."""
        file_path = LOCAL_UPLOAD_DIR / file_id
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Local file deleted: {file_id}")
                return True
            logger.warning(f"Delete failed: {file_id} not found locally.")
            return False
        except Exception as e:
            logger.error(f"Local Delete Error: {str(e)}")
            return False