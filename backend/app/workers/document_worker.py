import json
import redis
import os
import logging
from app.infrastructure.queue.celery_app import celery_app
from app.dependencies import get_document_processor, get_storage_service
from app.infrastructure.db.session_sync import db_session_scope
from app.infrastructure.db.models import Document
from app.infrastructure.config import settings
from app.infrastructure.logging import request_id_var
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.redis_url)

# Initialize services lazily inside the task for better DI and reliability
def get_services():
    return get_document_processor(), get_storage_service()

@celery_app.task(bind=True, name="process_document_task", max_retries=5)
def process_document_task(self, document_id: str, request_id: str = "worker-gen"):
    """Core background task for document analysis."""
    token = request_id_var.set(request_id)
    task_id = self.request.id
    channel = f"notifications_{task_id}"

    # Lazy load services
    processor, storage_service = get_services()

    try:
        with db_session_scope() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Task {task_id} failed: Document {document_id} not found.")
                return {"error": "Document not found"}

            doc.status = "PROCESSING"
            db.commit() # Commit status change immediately
            
            logger.info(f"Processing document: {document_id} (Task: {task_id})")

            # --- DE-DUPLICATION CHECK ---
            if doc.content_hash:
                existing_doc = db.query(Document).filter(
                    Document.content_hash == doc.content_hash,
                    Document.status == "COMPLETED",
                    Document.id != doc.id
                ).first()
                
                if existing_doc:
                    logger.info(f"RAG: Duplicate found (Hash: {doc.content_hash}). Cloning results from {existing_doc.id}")
                    doc.raw_text = existing_doc.raw_text
                    doc.analysis = existing_doc.analysis
                    doc.status = "COMPLETED"
                    
                    # Clone embeddings using raw SQL for maximum performance
                    from sqlalchemy import text as sa_text
                    db.execute(sa_text("""
                        INSERT INTO data_document_embeddings (id, document_id, text, embedding, meta)
                        SELECT gen_random_uuid(), :new_id, text, embedding, meta 
                        FROM data_document_embeddings 
                        WHERE document_id = :old_id
                    """), {"new_id": doc.id, "old_id": existing_doc.id})
                    
                    db.commit()
                    return {"document_id": document_id, "status": "CLONED", "source": str(existing_doc.id)}

            # Get file path
            path_to_process = async_to_sync(storage_service.get_file_path)(str(doc.id))

            if not os.path.exists(path_to_process):
                # Permanent failure: File missing
                doc.status = "FAILED"
                logger.error(f"FILE MISSING: {path_to_process}")
                raise Exception(f"NON_RETRYABLE: File not found at {path_to_process}")

            logger.info(f"Starting AI analysis for {doc.file_name}")
            
            # 1. AI Processing (Extraction & Summary)
            result = processor.process_sync(path_to_process, mime_type=doc.content)
            
            # Update document results
            doc.raw_text = result.get("raw_text", "")
            doc.analysis = result.get("analysis", {})
            doc.status = "COMPLETED"

            # 2. Semantic Indexing (RAG)
            from app.dependencies import get_rag_service
            from llama_index.core import Document as LlamaDocument
            from llama_index.core.node_parser import SentenceSplitter
            
            rag_service = get_rag_service()
            
            # Split into chunks
            parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
            nodes = parser.get_nodes_from_documents([LlamaDocument(text=doc.raw_text)])
            
            logger.info(f"Split document into {len(nodes)} chunks for RAG indexing")
            
            # Index the nodes
            rag_service.index_nodes(db, str(doc.id), nodes)

            # 3. Cost Optimization: Update User Token Count
            tokens_used = doc.analysis.get("estimated_tokens", 0)
            from app.infrastructure.db.models import User
            db.query(User).filter(User.id == doc.owner_id).update({
                User.total_tokens: User.total_tokens + tokens_used
            })
            
            logger.info(f"Successfully processed and indexed document {document_id}. Tokens: {tokens_used}")

            # Notify via Redis
            notification_payload = {
                "task_id": task_id,
                "status": "COMPLETED",
                "analysis": result.get("analysis", {})
            }
            redis_client.publish(channel, json.dumps(notification_payload))

            return {"document_id": document_id, "status": "COMPLETED"}

    except Exception as e:
        error_msg = str(e)
        is_transient = any(msg in error_msg for msg in ["Rate Limit", "429", "timeout", "connection", "AI Engine failed"])
        is_permanent = "NON_RETRYABLE" in error_msg or "too short" in error_msg or "not found" in error_msg

        if is_permanent or not is_transient or self.request.retries >= self.max_retries:
            # Permanent failure or max retries reached
            logger.critical(f"Task {task_id} permanently failed: {error_msg}")
            
            # Ensure status is updated to FAILED in a fresh session if needed
            with db_session_scope() as db:
                doc = db.query(Document).filter(Document.id == document_id).first()
                if doc:
                    doc.status = "FAILED"
                    doc.error_message = error_msg
            
            error_payload = {"task_id": task_id, "status": "FAILED", "error": error_msg}
            redis_client.publish(channel, json.dumps(error_payload))
            return {"error": error_msg}

        # Otherwise, retry
        logger.warning(f"Task {task_id} encountered transient error. Retrying... Error: {error_msg}")
        
        # Mark as FAILED in DB so duplicate check allows re-upload if user is impatient
        with db_session_scope() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "FAILED"
                doc.error_message = f"Transient Error (Retrying...): {error_msg}"

        retry_payload = {"task_id": task_id, "status": "RETRYING", "message": "Transient error, retrying..."}
        redis_client.publish(channel, json.dumps(retry_payload))
        
        # Exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=min(countdown, 3600))
    
    finally:
        request_id_var.reset(token)