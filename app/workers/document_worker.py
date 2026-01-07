import json
import redis
import os
import logging
from app.infrastructure.queue.celery_app import celery_app
from app.dependencies import get_document_processor, get_storage_service
from app.infrastructure.db.session_sync import get_db_sync
from app.infrastructure.db.models import Document
from app.infrastructure.config import settings
from app.infrastructure.logging import request_id_var
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.redis_url)

# Initialize services once
processor = get_document_processor()
storage_service = get_storage_service()

@celery_app.task(bind=True, name="process_document_task", max_retries=3)
def process_document_task(self, document_id: str, request_id: str = "worker-gen"):
    """Core background task for document analysis."""
    token = request_id_var.set(request_id)
    db = get_db_sync()
    task_id = self.request.id
    channel = f"notifications_{task_id}"
    doc = None

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Task {task_id} failed: Document {document_id} not found in database.")
            return {"error": "Document not found"}

        doc.status = "PROCESSING"
        db.commit()
        logger.info(f"Processing document: {document_id} (Task: {task_id})")

        # Get file path
        path_to_process = async_to_sync(storage_service.get_file_path)(str(doc.id))

        if not os.path.exists(path_to_process):
            logger.error(f"FILE CRITICAL ERROR: Worker cannot find file at {path_to_process}")
            raise FileNotFoundError(f"Could not locate document file at {path_to_process}")

        logger.info(f"Verification successful. Starting AI analysis for {doc.file_name}")
        
        # FIXED: Use process_sync for Celery (synchronous context)
        result = processor.process_sync(path_to_process, mime_type=doc.content)

        # Update document
        doc.raw_text = result.get("raw_text", "")
        doc.analysis = result.get("analysis", {})
        doc.status = "COMPLETED"
        db.commit()
        
        logger.info(f"Successfully analyzed document {document_id}")
        logger.info(f"Summary preview: {result.get('analysis', {}).get('summary', '')[:100]}...")

        # Notification
        notification_payload = {
            "task_id": task_id,
            "status": "COMPLETED",
            "analysis": result.get("analysis", {})
        }
        redis_client.publish(channel, json.dumps(notification_payload))

        return {"document_id": document_id, "status": "COMPLETED"}

    except Exception as e:
        db.rollback()
        
        retries_left = self.request.retries < self.max_retries
        
        if not retries_left:
            logger.critical(f"Task {task_id} permanently failed after {self.max_retries} retries: {str(e)}")
            if doc:
                doc.status = "FAILED"
                db.commit()
            
            error_payload = {"task_id": task_id, "status": "FAILED", "error": str(e)}
            redis_client.publish(channel, json.dumps(error_payload))
        else:
            logger.warning(f"Task {task_id} encountered an error. Retrying... Error: {str(e)}")
            retry_payload = {"task_id": task_id, "status": "RETRYING", "message": "Processing error, retrying..."}
            redis_client.publish(channel, json.dumps(retry_payload))

        # Retry strategy
        if "Rate Limit" in str(e) or "429" in str(e):
            raise self.retry(exc=e, countdown=120)
        
        if "Event loop" in str(e):
            logger.error("Event loop error detected - this should be fixed with sync processing")
            raise self.retry(exc=e, countdown=30)
            
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()
        request_id_var.reset(token)