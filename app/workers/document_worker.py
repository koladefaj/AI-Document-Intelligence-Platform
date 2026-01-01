import json
import redis
import os
import logging
from asgiref.sync import async_to_sync
from app.infrastructure.queue.celery_app import celery_app
from app.dependencies import get_document_processor, get_storage_service
from app.infrastructure.db.session_sync import get_db_sync
from app.infrastructure.db.models import Document
from app.infrastructure.config import settings
from app.infrastructure.logging import request_id_var

# Initialize logger
logger = logging.getLogger(__name__)

# Redis is used here as a Message Broker for real-time WebSocket notifications
redis_client = redis.from_url(settings.redis_url)

# Initialize services once at module level for efficiency
processor = get_document_processor()
storage_service = get_storage_service()

@celery_app.task(bind=True, name="process_document_task", max_retries=3)
def process_document_task(self, document_id: str, request_id: str = "worker-gen"):
    """
    Core background task for document analysis.
    """
    # Traceability: Set the request_id so all logs in this thread share the same ID
    token = request_id_var.set(request_id)
    db = get_db_sync()
    task_id = self.request.id
    channel = f"notifications_{task_id}"
    doc = None

    try:
        # Fetch document from DB
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Task {task_id} failed: Document {document_id} not found in database.")
            return {"error": "Document not found"}

        # Set status to PROCESSING
        doc.status = "PROCESSING"
        db.commit()
        logger.info(f"Processing document: {document_id} (Task: {task_id})")

        # --- 1. STORAGE RESOLUTION ---
        path_to_process = async_to_sync(storage_service.get_file_path)(str(doc.id)) 

        if not os.path.exists(path_to_process):
            logger.error(f"FILE CRITICAL ERROR: Worker cannot find file at {path_to_process}")
            raise FileNotFoundError(f"Could not locate document file at {path_to_process}")

        # --- 2. AI PROCESSING ---
        logger.info(f"Verification successful. Starting AI analysis for {doc.file_name}")
        
        # FIXED: Wrapped in async_to_sync because processor.process is an async coroutine
        result = async_to_sync(processor.process)(path_to_process, mime_type=doc.content)

        # --- 3. PERSISTENCE ---
        doc.raw_text = result.get("raw_text", "")
        
        # FIXED: Don't use json.dumps() if your model uses the JSON column type
        # SQLAlchemy handles the dictionary-to-JSON conversion for you.
        doc.analysis = result.get("analysis", {}) 
        
        doc.status = "COMPLETED"
        db.commit()
        logger.info(f"Successfully analyzed document {document_id}")

        # --- 4. REAL-TIME NOTIFICATION ---
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
            retry_payload = {"task_id": task_id, "status": "RETRYING", "message": "API busy, retrying..."}
            redis_client.publish(channel, json.dumps(retry_payload))

        # --- RETRY STRATEGY ---
        if "Rate Limit" in str(e) or "429" in str(e):
            raise self.retry(exc=e, countdown=120) 
            
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()
        request_id_var.reset(token)