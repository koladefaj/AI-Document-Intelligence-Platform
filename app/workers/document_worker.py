from app.infrastructure.queue.celery_app import celery_app
from app.dependencies import get_document_processor
from app.infrastructure.db.session_sync import get_db_sync
from app.infrastructure.db.models import Document
from app.dependencies import get_storage_service
import multiprocessing

multiprocessing.set_start_method('spawn', force=True)
processor = get_document_processor()
storage_service = get_storage_service()

@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: str):
    """Background Processing of uploaded file"""
    db = get_db_sync()

    doc = db.query(Document).filter(Document.id == document_id).first()

    if not doc:
        return {"error": "Document not found"}

    result = processor.process(doc.local_path)

    doc.raw_text = result["raw_text"]
    doc.analysis = result["analysis"]
    doc.status = "COMPLETED"
    db.commit()
    db.close()

    return {"document_id": document_id, "status": "COMPLETED"}