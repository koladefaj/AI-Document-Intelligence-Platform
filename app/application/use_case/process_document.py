from app.workers.document_worker import process_document_task

def queue_processing(document_id: str):
    task = process_document_task.delay(document_id)
    return task.id