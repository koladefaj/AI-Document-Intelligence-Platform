import os
import logging
from pathlib import Path
from app.domain.services.storage_interface import StorageInterface

# Initialize logger for storage operations
logger = logging.getLogger(__name__)

# --- DIRECTORY CONFIGURATION ---
# Dev Note: Path(__file__) resolves the absolute path of this script.
# .parent.parent.parent.parent moves us from this file up to the project root.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# In Docker, we usually mount a volume to /app/app/files.
# This directory MUST have write permissions for the user running the container.
LOCAL_UPLOAD_DIR = BASE_DIR / "app" / "files"

# Ensure the directory exists on startup
# Dev Note: 'parents=True' creates any missing middle folders.
# 'exist_ok=True' prevents an error if the folder is already there.
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
        
        Dev Note: This is used by the Celery worker to find the file
        on the shared Docker volume to pass it to the AI Processor.
        """
        file_path = LOCAL_UPLOAD_DIR / file_id
        
        if not file_path.exists():
            logger.warning(f"File lookup failed: {file_id} not found at {file_path}")
            
        return str(file_path)