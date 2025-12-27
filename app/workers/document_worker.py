from app.infrastructure.queue.celery_app import celery_app
import time

@celery_app.task(name="process_document")
def process_document_task(document_id: str):
    time.sleep(5)
    print(f"Document {document_id} processed sucessfully")
    return {"status": "completed", "document_id": document_id}