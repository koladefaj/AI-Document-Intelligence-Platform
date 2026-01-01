import os
import logging
from app.infrastructure.processing.processor_service import DocumentProcessor
from app.infrastructure.storage.minio_service import MinioStorage
from app.infrastructure.storage.local_storage import LocalStorage
from app.domain.services.storage_interface import StorageInterface
from app.infrastructure.queue import celery_app

# Initialize logger for dependency tracking
logger = logging.getLogger(__name__)

# We initialize these once to avoid repeated connection overhead
_local_storage = LocalStorage()
_minio_storage = MinioStorage()

def get_storage_service() -> StorageInterface:
    """
    Dependency Provider for Storage.
    
    Logic:
    1. Checks the 'USE_MINIO' environment variable.
    2. If 'true', returns the MinioStorage (S3-compatible) instance.
    3. Otherwise, defaults to LocalStorage (local disk).
    
    Dev Note: In Docker Compose, ensure USE_MINIO=true is set if you want
    persistence across container rebuilds using the MinIO volume.
    """
    use_minio = os.getenv("USE_MINIO", "false").lower() == "true"
    
    if use_minio:
        logger.debug("Storage Dependency: Injecting MinioStorage")
        return _minio_storage
    
    logger.debug("Storage Dependency: Injecting LocalStorage")
    return _local_storage

def get_task_queue():
    """Returns the initialized Celery application for task dispatching."""
    return celery_app

def get_document_processor():
    """
    Returns a new instance of the DocumentProcessor.
    This service handles the orchestration between Gemini and Ollama.
    """
    return DocumentProcessor()