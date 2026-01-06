import os
import logging
from app.infrastructure.processing.processor_service import DocumentProcessor
from app.domain.services.storage_interface import StorageInterface

# Initialize logger
logger = logging.getLogger(__name__)

# Global variables to cache the instances
_storage_instance = None

def get_storage_service() -> StorageInterface:
    """
    Dependency Provider for Storage with Lazy Loading.
    """
    global _storage_instance
    
    # If we already created a storage service, return it
    if _storage_instance is not None:
        return _storage_instance

    # Determine which storage to use
    # Default to 'r2' if you are no longer using Minio
    storage_type = os.getenv("STORAGE_TYPE", "r2").lower()

    if storage_type == "minio":
        from app.infrastructure.storage.minio_service import MinioStorage
        logger.info("Storage Dependency: Initializing MinioStorage")
        _storage_instance = MinioStorage()
    elif storage_type == "local":
        from app.infrastructure.storage.local_storage import LocalStorage
        logger.info("Storage Dependency: Initializing LocalStorage")
        _storage_instance = LocalStorage()
    else:
        # Default to R2
        from app.infrastructure.storage.r2_storage import R2Storage
        logger.info("Storage Dependency: Initializing R2Storage")
        _storage_instance = R2Storage()
    
    return _storage_instance

def get_document_processor():
    return DocumentProcessor()