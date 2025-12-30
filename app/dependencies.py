import os

from app.infrastructure.processing.processor_service import DocumentProcessor
from app.infrastructure.storage.minio_service import MinioStorage
from app.infrastructure.storage.local_storage import LocalStorage
from app.domain.services.storage_interface import StorageInterface
from app.infrastructure.queue import celery_app

def get_storage_service() -> StorageInterface:
    """AUtoswtich based on whats available"""
    if os.getenv("USE_MINIO", "false").lower() == "true":
        return MinioStorage()
    return LocalStorage()

def get_task_queue():
    return celery_app

def get_document_processor():
    return DocumentProcessor()